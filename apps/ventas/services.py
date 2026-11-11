from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from apps.ventas.models import Venta, DetalleVenta
from apps.productos.models import Producto
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario

@transaction.atomic
def registrar_venta(*, usuario, almacen_id, lineas, cliente=None, caja=None,
                    numero_venta, tipo_comprobante="TICKET", descuento=Decimal("0")):
    """
    Crea una venta pagada/pendiente de pago y descuenta stock mediante FEFO.
    lineas: [{"producto_id": int, "cantidad": Decimal,
              "precio_unitario": Decimal, "descuento": Decimal opcional}]
    Cada línea se distribuye entre lotes disponibles por fecha de vencimiento.
    Los pagos se registran aparte mediante PagoVenta.
    """
    almacen = Almacen.objects.get(pk=almacen_id, estado=True)
    if caja is not None and caja.estado != "ABIERTA":
        raise ValidationError("No se puede vender con una caja cerrada.")
    if not lineas:
        raise ValidationError("Agrega al menos un producto a la venta.")

    venta = Venta.objects.create(
        cliente=cliente, usuario=usuario, caja=caja,
        numero_venta=numero_venta, tipo_comprobante=tipo_comprobante,
        fecha_venta=timezone.now(), estado="PENDIENTE",
    )
    subtotal_general = Decimal("0.00")

    for linea in lineas:
        producto = Producto.objects.get(pk=linea["producto_id"], estado=True)
        cantidad_pendiente = Decimal(str(linea["cantidad"]))
        precio = Decimal(str(linea["precio_unitario"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        descuento_linea = Decimal(str(linea.get("descuento", "0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if cantidad_pendiente <= 0 or precio < 0 or descuento_linea < 0:
            raise ValidationError("Cantidad, precio o descuento no válidos.")

        existencia = Inventario.objects.select_for_update().filter(
            producto=producto, almacen=almacen
        ).first()
        if not existencia or existencia.stock_actual - existencia.stock_reservado < cantidad_pendiente:
            raise ValidationError(f"Stock insuficiente para {producto.nombre}.")

        lotes = list(
            Lote.objects.select_for_update().filter(
                producto=producto, almacen=almacen, cantidad_disponible__gt=0,
                fecha_vencimiento__gte=timezone.localdate(), estado="DISPONIBLE"
            ).order_by("fecha_vencimiento", "id")
        )
        disponible_lotes = sum((l.cantidad_disponible for l in lotes), start=Decimal("0"))
        if disponible_lotes < cantidad_pendiente:
            raise ValidationError(f"No hay lotes vigentes suficientes para {producto.nombre}.")

        while cantidad_pendiente > 0:
            lote = next((l for l in lotes if l.cantidad_disponible > 0), None)
            tomar = min(lote.cantidad_disponible, cantidad_pendiente)
            bruto = (tomar * precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            descuento_parte = (descuento_linea * tomar / Decimal(str(linea["cantidad"]))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            importe = bruto - descuento_parte
            if importe < 0:
                raise ValidationError("El descuento no puede superar el importe de la línea.")
            DetalleVenta.objects.create(
                venta=venta, producto=producto, lote=lote,
                cantidad=tomar, precio_unitario=precio,
                descuento=descuento_parte, subtotal=importe,
            )
            lote.cantidad_disponible -= tomar
            if lote.cantidad_disponible == 0:
                lote.estado = "AGOTADO"
            lote.save(update_fields=["cantidad_disponible", "estado"])
            MovimientoInventario.objects.create(
                producto=producto, almacen=almacen, lote=lote,
                usuario=usuario, tipo_movimiento="SALIDA", cantidad=tomar,
                motivo=f"Venta {numero_venta}", referencia_tipo="VENTA",
                referencia_id=venta.pk,
            )
            subtotal_general += importe
            cantidad_pendiente -= tomar

        existencia.stock_actual -= Decimal(str(linea["cantidad"]))
        existencia.save(update_fields=["stock_actual", "updated_at"])

    descuento = Decimal(str(descuento)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if descuento < 0 or descuento > subtotal_general:
        raise ValidationError("Descuento general no válido.")
    venta.subtotal = subtotal_general.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    venta.descuento = descuento
    venta.total = (subtotal_general - descuento).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    venta.save(update_fields=["subtotal", "descuento", "total"])
    return venta
