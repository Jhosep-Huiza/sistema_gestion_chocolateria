from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from apps.compras.models import Compra, DetalleCompra, PagoCompra
from apps.caja.models import Caja, MovimientoCaja
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.configuracion.models import Configuracion, MetodoPago
from apps.ventas.models import DetalleVenta
from apps.usuarios.services import registrar_auditoria, contexto_auditoria

CENTAVO = Decimal("0.01")


def _importe(valor):
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@transaction.atomic
def crear_compra(*, proveedor_id, usuario, tipo_documento, numero_documento="",
                 lineas, observaciones="", igv_porcentaje=None):
    """Crea una compra y calcula sus importes a partir de líneas validadas."""
    from apps.proveedores.models import Proveedor

    proveedor = Proveedor.objects.get(pk=proveedor_id, estado=True)
    if not lineas:
        raise ValidationError("Agrega al menos un producto a la compra.")
    configuracion = Configuracion.objects.order_by("pk").first()
    porcentaje = Decimal(str(
        igv_porcentaje if igv_porcentaje is not None
        else (configuracion.porcentaje_igv if configuracion else "18.00")
    ))
    if porcentaje < 0 or porcentaje > 100:
        raise ValidationError("El porcentaje de IGV debe estar entre 0 y 100.")

    detalles = []
    subtotal = Decimal("0.00")
    descuento_total = Decimal("0.00")
    for linea in lineas:
        try:
            producto_id = linea.get("producto_id", linea.get("producto"))
            cantidad = Decimal(str(linea["cantidad"]))
            precio = _importe(linea["precio_unitario"])
            descuento = _importe(linea.get("descuento", "0"))
        except (KeyError, TypeError, ValueError, ArithmeticError) as error:
            raise ValidationError("Una de las líneas de compra tiene datos inválidos.") from error
        if cantidad <= 0 or precio < 0 or descuento < 0:
            raise ValidationError("Cantidad, precio y descuento deben ser válidos.")
        bruto = _importe(cantidad * precio)
        if descuento > bruto:
            raise ValidationError("El descuento de una línea no puede superar su importe.")
        from apps.productos.models import Producto
        try:
            producto = Producto.objects.get(pk=producto_id, estado=True)
        except (Producto.DoesNotExist, TypeError, ValueError) as error:
            raise ValidationError("Selecciona un producto activo para cada línea.") from error
        detalles.append((producto, cantidad, precio, descuento, bruto))
        subtotal += bruto
        descuento_total += descuento

    subtotal = _importe(subtotal)
    descuento_total = _importe(descuento_total)
    base_imponible = subtotal - descuento_total
    igv = _importe(base_imponible * porcentaje / Decimal("100"))
    total = base_imponible + igv

    compra = Compra.objects.create(
        proveedor=proveedor, usuario=usuario,
        numero_compra=f"TMP-{uuid4().hex}", tipo_documento=tipo_documento,
        numero_documento=numero_documento, fecha_compra=timezone.now(),
        subtotal=subtotal, descuento=descuento_total, igv=igv, total=total,
        observaciones=observaciones,
    )
    compra.numero_compra = f"COMP-{compra.pk:06d}"
    compra.save(update_fields=["numero_compra"])
    for producto, cantidad, precio, descuento, bruto in detalles:
        DetalleCompra.objects.create(
            compra=compra, producto=producto, cantidad=cantidad,
            precio_unitario=precio, descuento=descuento, subtotal=bruto,
        )
    return compra


@transaction.atomic
def registrar_pago_compra(*, compra_id, usuario, metodo_pago_id, monto,
                          referencia="", caja_id=None, direccion_ip=None):
    """Registra un pago sin exceder el saldo pendiente de la compra."""
    compra = Compra.objects.select_for_update().get(pk=compra_id)
    metodo = MetodoPago.objects.get(pk=metodo_pago_id, estado=True)
    monto = _importe(monto)
    pagado = compra.pagos.filter(estado="CONFIRMADO").aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    saldo = compra.total - pagado
    if compra.estado == "ANULADA":
        raise ValidationError("No se puede pagar una compra anulada.")
    if monto <= 0 or monto > saldo:
        raise ValidationError(f"El pago debe ser mayor a cero y no superar el saldo de S/ {saldo:.2f}.")
    caja = None
    if metodo.nombre.strip().casefold() == "efectivo":
        caja = Caja.objects.select_for_update().filter(pk=caja_id, estado="ABIERTA").first() if caja_id else None
        if caja_id and caja is None:
            raise ValidationError("La caja seleccionada está cerrada o no existe.")
        if caja is None:
            caja = Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").first()
        if caja is None:
            raise ValidationError("Selecciona una caja abierta para registrar el pago en efectivo.")
    pago = PagoCompra.objects.create(
        compra=compra, metodo_pago=metodo, usuario=usuario,
        monto=monto, fecha_pago=timezone.now(), referencia=referencia,
    )
    if caja:
        MovimientoCaja.objects.create(
            caja=caja, usuario=usuario, tipo="EGRESO",
            concepto=f"Pago en efectivo · Compra {compra.numero_compra}", monto=monto,
            referencia_tipo="COMPRA_PAGO", referencia_id=pago.pk,
        )
    return pago

@transaction.atomic
def recibir_compra(*, compra_id, almacen_id, usuario, lotes_por_detalle, direccion_ip=None):
    """
    Confirma una compra pendiente y registra lotes, existencias y movimientos.
    lotes_por_detalle: {detalle_compra_id: [
      {"codigo_lote": "...", "fecha_vencimiento": date,
       "cantidad": Decimal, "fecha_fabricacion": date|None}
    ]}
    La suma de cantidades de los lotes debe coincidir con el detalle comprado.
    """
    compra = Compra.objects.select_for_update().get(pk=compra_id)
    almacen = Almacen.objects.get(pk=almacen_id, estado=True)
    if compra.estado != "PENDIENTE":
        raise ValidationError("Solo se pueden recibir compras pendientes.")

    detalles = list(compra.detalles.select_related("producto").all())
    if not detalles:
        raise ValidationError("La compra no tiene productos registrados.")

    for detalle in detalles:
        lotes_data = lotes_por_detalle.get(detalle.pk, [])
        total_lotes = sum((Decimal(str(item["cantidad"])) for item in lotes_data), start=Decimal("0"))
        if total_lotes != detalle.cantidad:
            raise ValidationError(
                f"Las cantidades de los lotes de {detalle.producto} deben sumar {detalle.cantidad}."
            )

        for item in lotes_data:
            vencimiento = item["fecha_vencimiento"]
            cantidad = Decimal(str(item["cantidad"]))
            fabricacion = item.get("fecha_fabricacion")
            if cantidad <= 0:
                raise ValidationError("La cantidad de cada lote debe ser mayor a cero.")
            if vencimiento <= timezone.localdate():
                raise ValidationError("No se puede recibir un lote vencido.")
            if fabricacion and fabricacion > vencimiento:
                raise ValidationError("La fecha de fabricación no puede superar el vencimiento.")
            lote = Lote.objects.create(
                detalle_compra=detalle,
                producto=detalle.producto,
                almacen=almacen,
                codigo_lote=item["codigo_lote"],
                fecha_fabricacion=fabricacion,
                fecha_vencimiento=vencimiento,
                cantidad_recibida=cantidad,
                cantidad_disponible=cantidad,
                estado="DISPONIBLE",
            )
            existencia, _ = Inventario.objects.select_for_update().get_or_create(
                producto=detalle.producto, almacen=almacen,
                defaults={"stock_actual": 0, "stock_reservado": 0},
            )
            existencia = Inventario.objects.select_for_update().get(pk=existencia.pk)
            existencia.stock_actual += cantidad
            existencia.save(update_fields=["stock_actual", "updated_at"])
            MovimientoInventario.objects.create(
                producto=detalle.producto, almacen=almacen, lote=lote,
                usuario=usuario, tipo_movimiento="ENTRADA",
                cantidad=cantidad, motivo=f"Recepción de compra {compra.numero_compra}",
                referencia_tipo="COMPRA", referencia_id=compra.pk,
            )

    compra.estado = "RECIBIDA"
    compra.save(update_fields=["estado"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="RECEPCION_COMPRA_STOCK", tabla_afectada="inventario",
        registro_id=compra.pk, descripcion=f"Recepción de compra {compra.numero_compra} en {almacen}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return compra


@transaction.atomic
def anular_compra(*, compra_id, usuario, direccion_ip=None):
    """Anula una compra y revierte sus existencias solo si siguen intactas."""
    compra = Compra.objects.select_for_update().get(pk=compra_id)
    if compra.estado == "ANULADA":
        raise ValidationError("La compra ya está anulada.")
    if compra.estado not in {"PENDIENTE", "RECIBIDA"}:
        raise ValidationError("El estado actual de la compra no permite anularla.")

    lotes = list(Lote.objects.select_for_update().filter(detalle_compra__compra=compra))
    if compra.estado == "RECIBIDA":
        if not lotes:
            raise ValidationError("No se puede anular: la compra figura recibida pero no tiene lotes registrados.")
        ids_lotes = [lote.pk for lote in lotes]
        if DetalleVenta.objects.filter(lote_id__in=ids_lotes).exists():
            raise ValidationError("No se puede anular: uno o más lotes ya tienen ventas asociadas.")
        for lote in lotes:
            if lote.cantidad_disponible != lote.cantidad_recibida:
                raise ValidationError(
                    f"No se puede anular: el lote {lote.codigo_lote} tuvo consumo o movimientos posteriores."
                )
        existencias = {}
        for lote in lotes:
            clave = (lote.producto_id, lote.almacen_id)
            existencias[clave] = existencias.get(clave, Decimal("0")) + lote.cantidad_disponible
        filas = list(Inventario.objects.select_for_update().filter(
            producto_id__in={clave[0] for clave in existencias},
            almacen_id__in={clave[1] for clave in existencias},
        ))
        mapa_existencias = {(fila.producto_id, fila.almacen_id): fila for fila in filas}
        for clave, cantidad in existencias.items():
            fila = mapa_existencias.get(clave)
            if not fila or fila.stock_actual - fila.stock_reservado < cantidad:
                raise ValidationError("No se puede anular: el stock ya fue reservado o consumido.")
        for lote in lotes:
            clave = (lote.producto_id, lote.almacen_id)
            cantidad = lote.cantidad_disponible
            existencia = mapa_existencias[clave]
            existencia.stock_actual -= cantidad
            existencia.save(update_fields=["stock_actual", "updated_at"])
            lote.cantidad_disponible = Decimal("0")
            lote.estado = "AGOTADO"
            lote.save(update_fields=["cantidad_disponible", "estado"])
            MovimientoInventario.objects.create(
                producto=lote.producto, almacen=lote.almacen, lote=lote,
                usuario=usuario, tipo_movimiento="AJUSTE_NEGATIVO", cantidad=cantidad,
                motivo=f"Anulación de compra {compra.numero_compra}",
                referencia_tipo="COMPRA", referencia_id=compra.pk,
            )

    compra.estado = "ANULADA"
    compra.save(update_fields=["estado"])
    movimientos_pago = list(MovimientoCaja.objects.select_for_update().filter(
        referencia_tipo="COMPRA_PAGO", referencia_id__in=compra.pagos.values_list("pk", flat=True),
        tipo="EGRESO",
    ))
    caja_reversa = None
    for movimiento in movimientos_pago:
        caja_movimiento = Caja.objects.select_for_update().get(pk=movimiento.caja_id)
        if caja_movimiento.estado == "CERRADA":
            if caja_reversa is None:
                caja_reversa = Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").first()
            if caja_reversa is None:
                raise ValidationError("Abre una caja para registrar la reversa de los pagos en efectivo.")
            caja_movimiento = caja_reversa
        MovimientoCaja.objects.create(
            caja=caja_movimiento, usuario=usuario, tipo="INGRESO",
            concepto=f"Reversa de compra {compra.numero_compra}", monto=movimiento.monto,
            referencia_tipo="ANULACION_COMPRA", referencia_id=compra.pk,
        )
    compra.pagos.filter(estado="CONFIRMADO").update(estado="ANULADO")
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="ANULACION_COMPRA", tabla_afectada="compras",
        registro_id=compra.pk, descripcion=f"Compra {compra.numero_compra} anulada.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return compra
