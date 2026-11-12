from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from apps.ventas.models import Venta, DetalleVenta, PagoVenta, SecuenciaVenta
from apps.productos.models import Producto
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.caja.models import Caja, MovimientoCaja
from apps.configuracion.models import Configuracion, MetodoPago
from apps.usuarios.services import contexto_auditoria, registrar_auditoria

CENTAVO = Decimal("0.01")


def _importe(valor):
    try:
        return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ValidationError("Ingresa un importe válido.") from error


def _pagos_validados(pagos, total):
    datos = []
    suma = Decimal("0.00")
    for pago in pagos or []:
        try:
            metodo_id = pago.get("metodo_pago_id", pago.get("metodo_pago"))
            monto = _importe(pago["monto"])
        except (KeyError, AttributeError, ValidationError) as error:
            raise ValidationError("Los datos de un pago no son válidos.") from error
        if monto <= 0:
            raise ValidationError("Cada pago debe ser mayor a cero.")
        try:
            metodo = MetodoPago.objects.get(pk=metodo_id, estado=True)
        except (MetodoPago.DoesNotExist, TypeError, ValueError) as error:
            raise ValidationError("Selecciona un método de pago activo.") from error
        datos.append({"metodo": metodo, "monto": monto, "referencia": str(pago.get("referencia", ""))[:100]})
        suma += monto
    if suma > total:
        raise ValidationError("El total pagado no puede superar el total de la venta.")
    return datos, suma


def _caja_para_efectivo(*, usuario, caja, pagos):
    requiere_caja = any(pago["metodo"].nombre.strip().casefold() == "efectivo" for pago in pagos)
    if caja is not None:
        caja = Caja.objects.select_for_update().get(pk=caja.pk)
        if caja.estado != "ABIERTA":
            if requiere_caja:
                raise ValidationError("La caja asociada a esta venta está cerrada.")
            caja = None
    if requiere_caja and caja is None:
        caja = Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").first()
    if requiere_caja and caja is None:
        raise ValidationError("Abre una caja antes de registrar pagos en efectivo.")
    return caja


def _crear_pagos(*, venta, usuario, pagos, caja, direccion_ip=None):
    for pago in pagos:
        pago_creado = PagoVenta.objects.create(
            venta=venta, metodo_pago=pago["metodo"], usuario=usuario,
            monto=pago["monto"], fecha_pago=timezone.now(), referencia=pago["referencia"],
        )
        if pago["metodo"].nombre.strip().casefold() == "efectivo":
            if caja is None or caja.estado != "ABIERTA":
                raise ValidationError("Abre una caja antes de registrar pagos en efectivo.")
            MovimientoCaja.objects.create(
                caja=caja, usuario=usuario, tipo="INGRESO",
                concepto=f"Pago en efectivo · Venta {venta.numero_venta}",
                monto=pago["monto"], referencia_tipo="VENTA", referencia_id=venta.pk,
            )
    total_pagado = sum((pago["monto"] for pago in pagos), Decimal("0.00"))
    venta.estado = "PAGADA" if total_pagado >= venta.total else ("PARCIAL" if total_pagado > 0 else "PENDIENTE")
    venta.save(update_fields=["estado"])
    return total_pagado


def _siguiente_numero_venta():
    """Incrementa el contador correlativo con bloqueo de fila dentro de la transacción."""
    secuencia = SecuenciaVenta.objects.select_for_update().filter(pk=1).first()
    if secuencia is None:
        maximo_existente = 0
        for numero in Venta.objects.filter(numero_venta__startswith="VTA-").values_list("numero_venta", flat=True):
            try:
                maximo_existente = max(maximo_existente, int(numero.removeprefix("VTA-")))
            except ValueError:
                continue
        SecuenciaVenta.objects.get_or_create(pk=1, defaults={"ultimo_numero": maximo_existente})
        secuencia = SecuenciaVenta.objects.select_for_update().get(pk=1)
    secuencia.ultimo_numero += 1
    secuencia.save(update_fields=["ultimo_numero"])
    return f"VTA-{secuencia.ultimo_numero:06d}"


@transaction.atomic
def registrar_venta(*, usuario, almacen_id, lineas, cliente=None, caja=None,
                    numero_venta=None, tipo_comprobante="TICKET", descuento=Decimal("0"),
                    pagos=None, usar_stock_reservado=False, direccion_ip=None):
    """Crea la venta, descuenta lotes FEFO, calcula IGV y registra sus pagos."""
    almacen = Almacen.objects.get(pk=almacen_id, estado=True)
    if not lineas:
        raise ValidationError("Agrega al menos un producto a la venta.")

    configuracion = Configuracion.objects.order_by("pk").first()
    porcentaje_igv = configuracion.porcentaje_igv if configuracion else Decimal("18.00")
    porcentaje_igv = Decimal(porcentaje_igv)
    if porcentaje_igv < 0 or porcentaje_igv > 100:
        raise ValidationError("El porcentaje de IGV configurado no es válido.")

    preparados = []
    subtotal_bruto = Decimal("0.00")
    descuentos_linea = Decimal("0.00")
    for linea in lineas:
        try:
            producto_id = linea["producto_id"]
            cantidad = Decimal(str(linea["cantidad"]))
            precio = _importe(linea.get("precio_unitario", linea.get("precio")))
            descuento_linea = _importe(linea.get("descuento", "0"))
        except (KeyError, TypeError, ValueError, ArithmeticError, ValidationError) as error:
            raise ValidationError("Una línea de venta tiene datos inválidos.") from error
        if cantidad <= 0 or cantidad.quantize(Decimal("0.001")) != cantidad or precio < 0 or descuento_linea < 0:
            raise ValidationError("Cantidad, precio o descuento no válidos.")
        try:
            producto = Producto.objects.get(pk=producto_id, estado=True)
        except (Producto.DoesNotExist, TypeError, ValueError) as error:
            raise ValidationError("Selecciona un producto activo.") from error
        importe_bruto = (cantidad * precio).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if descuento_linea > importe_bruto:
            raise ValidationError(f"El descuento de {producto.nombre} supera el importe de su línea.")
        preparados.append((producto, cantidad, precio, descuento_linea, importe_bruto))
        subtotal_bruto += importe_bruto
        descuentos_linea += descuento_linea

    descuento_global = _importe(descuento)
    base_antes_igv = subtotal_bruto - descuentos_linea - descuento_global
    if descuento_global < 0 or base_antes_igv < 0:
        raise ValidationError("El descuento global no puede superar el importe de la venta.")
    descuento_total = descuentos_linea + descuento_global
    igv = (base_antes_igv * porcentaje_igv / Decimal("100")).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    total = base_antes_igv + igv
    pagos_validados, monto_pagado = _pagos_validados(pagos, total)
    caja = _caja_para_efectivo(usuario=usuario, caja=caja, pagos=pagos_validados)

    numero_automatico = _siguiente_numero_venta()
    venta = Venta.objects.create(
        cliente=cliente, usuario=usuario, caja=caja,
        numero_venta=numero_automatico, tipo_comprobante=tipo_comprobante,
        fecha_venta=timezone.now(), subtotal=subtotal_bruto,
        descuento=descuento_total, igv=igv, total=total, estado="PENDIENTE",
    )

    for producto, cantidad, precio, descuento_linea, _ in preparados:
        existencia = Inventario.objects.select_for_update().filter(
            producto=producto, almacen=almacen,
        ).first()
        if not existencia:
            raise ValidationError(f"No hay stock registrado para {producto.nombre} en {almacen}.")
        disponible_stock = existencia.stock_actual if usar_stock_reservado else existencia.stock_actual - existencia.stock_reservado
        if disponible_stock < cantidad:
            raise ValidationError(f"Stock insuficiente para {producto.nombre}.")

        lotes = list(Lote.objects.select_for_update().filter(
            producto=producto, almacen=almacen, cantidad_disponible__gt=0,
            fecha_vencimiento__gte=timezone.localdate(), estado="DISPONIBLE",
        ).order_by("fecha_vencimiento", "pk"))
        disponible_lotes = sum((lote.cantidad_disponible for lote in lotes), Decimal("0"))
        if disponible_lotes < cantidad:
            raise ValidationError(f"No hay lotes FEFO vigentes suficientes para {producto.nombre}.")

        pendiente = cantidad
        descuento_pendiente = descuento_linea
        bruto_pendiente = (cantidad * precio).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        reserva_pendiente = min(cantidad, existencia.stock_reservado) if usar_stock_reservado else Decimal("0.000")
        while pendiente > 0:
            lote = next((candidato for candidato in lotes if candidato.cantidad_disponible > 0), None)
            tomar = min(lote.cantidad_disponible, pendiente)
            bruto_parte = bruto_pendiente if tomar == pendiente else (
                tomar * precio
            ).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            descuento_parte = descuento_pendiente if tomar == pendiente else (
                descuento_linea * tomar / cantidad
            ).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            descuento_parte = min(descuento_parte, descuento_pendiente)
            reserva_parte = min(tomar, reserva_pendiente)
            DetalleVenta.objects.create(
                venta=venta, producto=producto, lote=lote, cantidad=tomar,
                precio_unitario=precio, descuento=descuento_parte,
                subtotal=bruto_parte - descuento_parte, cantidad_reservada=reserva_parte,
            )
            lote.cantidad_disponible -= tomar
            if lote.cantidad_disponible == 0:
                lote.estado = "AGOTADO"
            lote.save(update_fields=["cantidad_disponible", "estado"])
            MovimientoInventario.objects.create(
                producto=producto, almacen=almacen, lote=lote, usuario=usuario,
                tipo_movimiento="SALIDA", cantidad=tomar,
                motivo=f"Venta {venta.numero_venta}", referencia_tipo="VENTA", referencia_id=venta.pk,
            )
            pendiente -= tomar
            descuento_pendiente -= descuento_parte
            bruto_pendiente -= bruto_parte
            reserva_pendiente -= reserva_parte

        existencia.stock_actual -= cantidad
        if usar_stock_reservado:
            existencia.stock_reservado -= min(cantidad, existencia.stock_reservado)
        existencia.save(update_fields=["stock_actual", "stock_reservado", "updated_at"])

    _crear_pagos(venta=venta, usuario=usuario, pagos=pagos_validados, caja=caja)
    return venta


@transaction.atomic
def registrar_pago_venta(*, venta_id, usuario, metodo_pago_id, monto, referencia="",
                         caja=None, direccion_ip=None):
    """Registra un pago posterior, actualiza el estado y agrega efectivo a caja."""
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    metodo = MetodoPago.objects.get(pk=metodo_pago_id, estado=True)
    monto = _importe(monto)
    pagado = venta.pagos.filter(estado="CONFIRMADO").aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    saldo = venta.total - pagado
    if venta.estado == "ANULADA":
        raise ValidationError("No se puede pagar una venta anulada.")
    if monto <= 0 or monto > saldo:
        raise ValidationError(f"El pago debe ser mayor a cero y no superar el saldo de S/ {saldo:.2f}.")
    caja_asociada = caja
    if caja_asociada is None and venta.caja_id and venta.caja.estado == "ABIERTA":
        caja_asociada = venta.caja
    caja = _caja_para_efectivo(
        usuario=usuario, caja=caja_asociada,
        pagos=[{"metodo": metodo, "monto": monto, "referencia": referencia}],
    )
    PagoVenta.objects.create(
        venta=venta, metodo_pago=metodo, usuario=usuario, monto=monto,
        fecha_pago=timezone.now(), referencia=referencia,
    )
    if metodo.nombre.strip().casefold() == "efectivo":
        MovimientoCaja.objects.create(
            caja=caja, usuario=usuario, tipo="INGRESO",
            concepto=f"Pago en efectivo · Venta {venta.numero_venta}", monto=monto,
            referencia_tipo="VENTA", referencia_id=venta.pk,
        )
    pagado += monto
    venta.estado = "PAGADA" if pagado == venta.total else "PARCIAL"
    if caja is not None and (venta.caja_id is None or venta.caja.estado != "ABIERTA"):
        venta.caja = caja
        venta.save(update_fields=["estado", "caja"])
    else:
        venta.save(update_fields=["estado"])
    return venta


@transaction.atomic
def anular_venta(*, venta_id, usuario, motivo, direccion_ip=None):
    """Anula una venta, devuelve cantidades a sus lotes y compensa caja."""
    if not getattr(usuario, "es_administrador", False):
        raise ValidationError("Solo un Administrador puede anular ventas.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    if len(motivo) > 255:
        raise ValidationError("El motivo no puede superar 255 caracteres.")
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado == "ANULADA":
        raise ValidationError("La venta ya está anulada.")
    detalles = list(venta.detalles.select_related("producto", "lote").all())
    cantidades = {}
    reservas = {}
    lotes = {}
    for detalle in detalles:
        clave = (detalle.producto_id, detalle.lote.almacen_id)
        cantidades[clave] = cantidades.get(clave, Decimal("0.000")) + detalle.cantidad
        reservas[clave] = reservas.get(clave, Decimal("0.000")) + detalle.cantidad_reservada
        lotes[detalle.lote_id] = detalle.lote
    inventarios = list(Inventario.objects.select_for_update().filter(
        producto_id__in={clave[0] for clave in cantidades},
        almacen_id__in={clave[1] for clave in cantidades},
    ))
    mapa_inventario = {(fila.producto_id, fila.almacen_id): fila for fila in inventarios}
    for clave in cantidades:
        if clave not in mapa_inventario:
            raise ValidationError("No se puede restituir la venta: falta el registro de inventario del almacén.")
    lotes_bloqueados = {
        lote.pk: lote for lote in Lote.objects.select_for_update().filter(pk__in=lotes)
    }
    for detalle in detalles:
        lote = lotes_bloqueados[detalle.lote_id]
        lote.cantidad_disponible += detalle.cantidad
        if lote.estado == "AGOTADO" and lote.fecha_vencimiento >= timezone.localdate():
            lote.estado = "DISPONIBLE"
        lote.save(update_fields=["cantidad_disponible", "estado"])
        MovimientoInventario.objects.create(
            producto=detalle.producto, almacen=lote.almacen, lote=lote, usuario=usuario,
            tipo_movimiento="DEVOLUCION", cantidad=detalle.cantidad,
            motivo=f"Anulación de venta {venta.numero_venta}: {motivo}",
            referencia_tipo="ANULACION_VENTA", referencia_id=venta.pk,
        )
    for clave, cantidad in cantidades.items():
        inventario = mapa_inventario[clave]
        inventario.stock_actual += cantidad
        inventario.stock_reservado += reservas.get(clave, Decimal("0.000"))
        inventario.save(update_fields=["stock_actual", "stock_reservado", "updated_at"])

    movimientos_efectivo = list(MovimientoCaja.objects.select_for_update().filter(
        referencia_tipo="VENTA", referencia_id=venta.pk, tipo="INGRESO",
    ))
    for ingreso in movimientos_efectivo:
        MovimientoCaja.objects.create(
            caja=ingreso.caja, usuario=usuario, tipo="EGRESO",
            concepto=f"Reverso de venta {venta.numero_venta}: {motivo}",
            monto=ingreso.monto, referencia_tipo="ANULACION_VENTA", referencia_id=venta.pk,
        )
    venta.pagos.filter(estado="CONFIRMADO").update(estado="ANULADO")
    venta.estado = "ANULADA"
    venta.observaciones = f"{venta.observaciones}\nAnulación: {motivo}".strip()
    venta._auditoria_registrada = True
    venta.save(update_fields=["estado", "observaciones"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(usuario=usuario, accion="ANULACION_VENTA", tabla_afectada="ventas",
                        registro_id=venta.pk, descripcion=f"Venta {venta.numero_venta} anulada. Motivo: {motivo}.",
                        direccion_ip=direccion_ip or ip_contexto)
    return venta
