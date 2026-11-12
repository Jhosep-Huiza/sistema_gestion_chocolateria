from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.caja.models import MovimientoCaja
from apps.inventario.models import Inventario, Lote, MovimientoInventario
from apps.usuarios.services import contexto_auditoria, registrar_auditoria
from apps.ventas.models import DetalleVenta, Venta

from .models import Devolucion, DetalleDevolucion

CENTAVO = Decimal("0.01")
MILIESIMO = Decimal("0.001")


def _cantidad(valor):
    try:
        cantidad = Decimal(str(valor))
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ValidationError("Ingresa una cantidad válida.") from error
    if cantidad <= 0 or cantidad.quantize(MILIESIMO) != cantidad:
        raise ValidationError("La cantidad debe ser positiva y admitir hasta tres decimales.")
    return cantidad


@transaction.atomic
def solicitar_devolucion(*, venta_id, usuario, motivo, tipo_reembolso, detalles, reembolso_efectivo=False):
    """Registra solicitud y reserva sus cantidades frente a otras solicitudes."""
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    motivo = (motivo or "").strip()
    if venta.estado == "ANULADA":
        raise ValidationError("No se puede devolver una venta anulada.")
    if not motivo:
        raise ValidationError("El motivo de devolución es obligatorio.")
    if tipo_reembolso not in dict(Devolucion.TIPOS):
        raise ValidationError("Selecciona un tipo de devolución válido.")
    if not detalles:
        raise ValidationError("Selecciona al menos un producto y una cantidad.")

    normalizados = {}
    for item in detalles:
        try:
            detalle_id = int(item["detalle_venta_id"])
            cantidad = _cantidad(item["cantidad"])
            estado_producto = item["estado_producto"]
        except (KeyError, TypeError, ValueError) as error:
            raise ValidationError("Los datos de un detalle de devolución no son válidos.") from error
        if estado_producto not in dict(DetalleDevolucion.ESTADOS_PRODUCTO):
            raise ValidationError("Selecciona un estado válido para cada producto.")
        normalizados[detalle_id] = normalizados.get(detalle_id, Decimal("0.000")) + cantidad

    ventas_detalle = {
        fila.pk: fila for fila in DetalleVenta.objects.select_for_update().filter(
            venta=venta, pk__in=normalizados,
        )
    }
    if len(ventas_detalle) != len(normalizados):
        raise ValidationError("Uno de los productos no pertenece a la venta seleccionada.")
    monto_base = Decimal("0.00")
    seleccionados = []
    for detalle_id, cantidad in normalizados.items():
        detalle_venta = ventas_detalle[detalle_id]
        ya_solicitado = DetalleDevolucion.objects.filter(
            detalle_venta=detalle_venta,
            devolucion__estado__in=["PENDIENTE", "APROBADA"],
        ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0.000")
        restante = detalle_venta.cantidad - ya_solicitado
        if cantidad > restante:
            raise ValidationError(
                f"La cantidad solicitada de {detalle_venta.producto} supera lo vendido menos lo ya devuelto o solicitado ({restante})."
            )
        seleccionados.append((detalle_venta, cantidad))
        monto_base += (detalle_venta.subtotal * cantidad / detalle_venta.cantidad).quantize(
            CENTAVO, rounding=ROUND_HALF_UP,
        )

    # El IGV se devuelve de forma proporcional al valor neto de las líneas seleccionadas.
    base_total = sum((fila.subtotal for fila in venta.detalles.all()), Decimal("0.00"))
    igv_proporcional = (venta.igv * monto_base / base_total).quantize(CENTAVO, rounding=ROUND_HALF_UP) if base_total else Decimal("0.00")
    devolucion = Devolucion.objects.create(
        venta=venta, usuario=usuario, fecha_devolucion=timezone.now(), motivo=motivo,
        tipo_reembolso=tipo_reembolso, total_devolucion=monto_base + igv_proporcional,
        reembolso_efectivo=reembolso_efectivo,
    )
    for detalle_venta, cantidad in seleccionados:
        estado_producto = next(
            item["estado_producto"] for item in detalles
            if int(item["detalle_venta_id"]) == detalle_venta.pk
        )
        DetalleDevolucion.objects.create(
            devolucion=devolucion, detalle_venta=detalle_venta,
            cantidad=cantidad, estado_producto=estado_producto,
        )
    return devolucion


@transaction.atomic
def aprobar_devolucion(*, devolucion_id, usuario, efectivo=False, direccion_ip=None):
    """Aprueba la devolución, actualiza stock y registra el reembolso si aplica."""
    if not (getattr(usuario, "es_administrador", False) or usuario.is_superuser):
        raise ValidationError("Solo un Administrador puede aprobar devoluciones.")
    devolucion = Devolucion.objects.select_for_update().select_related("venta").get(pk=devolucion_id)
    if devolucion.estado != "PENDIENTE":
        raise ValidationError("La devolución ya fue procesada.")
    venta = Venta.objects.select_for_update().get(pk=devolucion.venta_id)
    detalles = list(devolucion.detalles.select_for_update().select_related(
        "detalle_venta__lote", "detalle_venta__producto", "detalle_venta__lote__almacen",
    ))
    if not detalles:
        raise ValidationError("La devolución no contiene productos.")

    for item in detalles:
        detalle_venta = item.detalle_venta
        if item.estado_producto == "DANADO":
            continue
        lote_origen = Lote.objects.select_for_update().select_related("producto", "almacen", "detalle_compra").get(
            pk=detalle_venta.lote_id,
        )
        inventario, _ = Inventario.objects.select_for_update().get_or_create(
            producto_id=detalle_venta.producto_id, almacen_id=lote_origen.almacen_id,
            defaults={"stock_actual": Decimal("0.000"), "stock_reservado": Decimal("0.000")},
        )
        inventario = Inventario.objects.select_for_update().get(pk=inventario.pk)
        if item.estado_producto == "REINGRESAR":
            lote = lote_origen
            lote.cantidad_recibida += item.cantidad
            lote.cantidad_disponible += item.cantidad
            if lote.estado == "AGOTADO" and lote.fecha_vencimiento >= timezone.localdate():
                lote.estado = "DISPONIBLE"
        else:
            sufijo = f"-DEV-{devolucion.pk}-{item.pk}"
            codigo = f"{lote_origen.codigo_lote[:60-len(sufijo)]}{sufijo}"
            lote = Lote.objects.create(
                detalle_compra=lote_origen.detalle_compra, producto=lote_origen.producto,
                almacen=lote_origen.almacen, codigo_lote=codigo,
                fecha_fabricacion=lote_origen.fecha_fabricacion,
                fecha_vencimiento=lote_origen.fecha_vencimiento,
                cantidad_recibida=item.cantidad, cantidad_disponible=item.cantidad,
                estado="CUARENTENA",
            )
        lote.save(update_fields=["cantidad_recibida", "cantidad_disponible", "estado"])
        inventario.stock_actual += item.cantidad
        inventario.save(update_fields=["stock_actual", "updated_at"])
        MovimientoInventario.objects.create(
            producto=detalle_venta.producto, almacen=lote.almacen, lote=lote, usuario=usuario,
            tipo_movimiento="DEVOLUCION", cantidad=item.cantidad,
            motivo=f"Devolución {devolucion.pk} · {item.estado_producto}: {devolucion.motivo[:180]}",
            referencia_tipo="DEVOLUCION", referencia_id=devolucion.pk,
        )

    if efectivo and devolucion.tipo_reembolso == "REEMBOLSO":
        caja = venta.caja
        if caja is None:
            caja = getattr(devolucion.usuario, "cajas", None)
            caja = caja.order_by("-fecha_apertura").first() if caja is not None else None
        if caja is None:
            raise ValidationError("No se encontró una caja para registrar el reembolso en efectivo.")
        MovimientoCaja.objects.create(
            caja=caja, usuario=usuario, tipo="EGRESO",
            concepto=f"Reembolso en efectivo · Venta {venta.numero_venta}",
            monto=devolucion.total_devolucion,
            referencia_tipo="DEVOLUCION", referencia_id=devolucion.pk,
        )
        pagos = list(venta.pagos.filter(estado="CONFIRMADO").order_by("pk"))
        efectivo_restante = devolucion.total_devolucion
        for pago in pagos:
            if pago.metodo_pago.nombre.strip().casefold() != "efectivo" or efectivo_restante <= 0:
                continue
            aplicado = min(pago.monto, efectivo_restante)
            if aplicado == pago.monto:
                pago.estado = "ANULADO"
                pago.save(update_fields=["estado"])
            efectivo_restante -= aplicado

    devolucion.estado = "APROBADA"
    devolucion.save(update_fields=["estado"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="APROBACION_DEVOLUCION", tabla_afectada="devoluciones",
        registro_id=devolucion.pk,
        descripcion=f"Devolución {devolucion.pk} aprobada para venta {venta.numero_venta}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return devolucion


@transaction.atomic
def rechazar_devolucion(*, devolucion_id, usuario, motivo="", direccion_ip=None):
    """Rechaza una solicitud pendiente sin alterar inventario ni pagos."""
    if not (getattr(usuario, "es_administrador", False) or usuario.is_superuser):
        raise ValidationError("Solo un Administrador puede rechazar devoluciones.")
    devolucion = Devolucion.objects.select_for_update().get(pk=devolucion_id)
    if devolucion.estado != "PENDIENTE":
        raise ValidationError("La devolución ya fue procesada.")
    motivo = (motivo or "").strip()
    devolucion.estado = "RECHAZADA"
    if motivo:
        devolucion.motivo = f"{devolucion.motivo}\nRechazo: {motivo}"
    devolucion.save(update_fields=["estado", "motivo"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="RECHAZO_DEVOLUCION", tabla_afectada="devoluciones",
        registro_id=devolucion.pk, descripcion=f"Devolución {devolucion.pk} rechazada. {motivo}",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return devolucion
