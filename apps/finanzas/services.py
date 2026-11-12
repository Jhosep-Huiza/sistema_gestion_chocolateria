from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.caja.models import Caja, MovimientoCaja
from apps.usuarios.services import contexto_auditoria, registrar_auditoria
from .models import Gasto

CENTAVO = Decimal("0.01")


def _dinero(valor):
    try:
        importe = Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ValidationError("Ingresa un monto válido.") from error
    if importe <= 0:
        raise ValidationError("El monto debe ser mayor a cero.")
    return importe


def _caja_abierta(caja_id, usuario):
    caja = Caja.objects.select_for_update().filter(pk=caja_id, estado="ABIERTA").first() if caja_id else None
    if caja_id and caja is None:
        raise ValidationError("La caja seleccionada está cerrada o no existe.")
    if caja is None:
        caja = Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").first()
    return caja


@transaction.atomic
def registrar_gasto(*, usuario, categoria, descripcion, monto, fecha_gasto,
                    comprobante=None, es_efectivo=False, caja_id=None):
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValidationError("La categoría es obligatoria.")
    importe = _dinero(monto)
    caja = _caja_abierta(caja_id, usuario) if es_efectivo else None
    if es_efectivo and caja is None:
        raise ValidationError("Abre una caja o selecciona una caja abierta para registrar el gasto en efectivo.")
    gasto = Gasto.objects.create(
        usuario=usuario, caja=caja, categoria=categoria, descripcion=descripcion or "",
        monto=importe, fecha_gasto=fecha_gasto, comprobante=comprobante,
        es_efectivo=es_efectivo,
    )
    if es_efectivo:
        MovimientoCaja.objects.create(
            caja=caja, usuario=usuario, tipo="EGRESO", concepto=f"Gasto · {categoria}"[:150],
            monto=importe, referencia_tipo="GASTO", referencia_id=gasto.pk,
        )
    return gasto


def _caja_para_reversa(gasto, usuario):
    caja = Caja.objects.select_for_update().filter(pk=gasto.caja_id, estado="ABIERTA").first() if gasto.caja_id else None
    if caja is None:
        caja = Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").first()
    if caja is None:
        raise ValidationError("Para revertir este gasto en efectivo debe haber una caja abierta.")
    return caja


@transaction.atomic
def actualizar_gasto(*, gasto_id, usuario, categoria, descripcion, monto,
                      fecha_gasto, comprobante=None, es_efectivo=False, caja_id=None):
    gasto = Gasto.objects.select_for_update().get(pk=gasto_id)
    if gasto.estado != "REGISTRADO":
        raise ValidationError("No se puede editar un gasto anulado.")
    categoria = (categoria or "").strip()
    if not categoria:
        raise ValidationError("La categoría es obligatoria.")
    importe = _dinero(monto)
    caja_nueva = _caja_abierta(caja_id, usuario) if es_efectivo else None
    if es_efectivo and caja_nueva is None:
        raise ValidationError("Abre una caja o selecciona una caja abierta para registrar el gasto en efectivo.")
    caja_reversa = None
    if gasto.es_efectivo:
        caja_reversa = _caja_para_reversa(gasto, usuario)
    if caja_reversa:
        MovimientoCaja.objects.create(
            caja=caja_reversa, usuario=usuario, tipo="INGRESO",
            concepto=f"Reversa edición de gasto · {gasto.categoria}"[:150], monto=gasto.monto,
            referencia_tipo="REVERSA_GASTO", referencia_id=gasto.pk,
        )
    gasto.categoria = categoria
    gasto.descripcion = descripcion or ""
    gasto.monto = importe
    gasto.fecha_gasto = fecha_gasto
    gasto.es_efectivo = es_efectivo
    gasto.caja = caja_nueva
    if comprobante:
        gasto.comprobante = comprobante
    gasto.save()
    if es_efectivo:
        MovimientoCaja.objects.create(
            caja=caja_nueva, usuario=usuario, tipo="EGRESO", concepto=f"Gasto · {categoria}"[:150],
            monto=importe, referencia_tipo="GASTO", referencia_id=gasto.pk,
        )
    return gasto


@transaction.atomic
def anular_gasto(*, gasto_id, usuario, motivo=""):
    gasto = Gasto.objects.select_for_update().get(pk=gasto_id)
    if gasto.estado != "REGISTRADO":
        raise ValidationError("El gasto ya está anulado.")
    if gasto.es_efectivo:
        caja = _caja_para_reversa(gasto, usuario)
        MovimientoCaja.objects.create(
            caja=caja, usuario=usuario, tipo="INGRESO",
            concepto=f"Reversa gasto · {gasto.categoria}"[:150], monto=gasto.monto,
            referencia_tipo="ANULACION_GASTO", referencia_id=gasto.pk,
        )
    gasto.estado = "ANULADO"
    if motivo.strip():
        gasto.descripcion = f"{gasto.descripcion}\nAnulación: {motivo.strip()}".strip()
    gasto.save(update_fields=["estado", "descripcion"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="ANULACION_GASTO", tabla_afectada="gastos", registro_id=gasto.pk,
        descripcion=f"Gasto {gasto.pk} anulado. {motivo.strip()}", direccion_ip=ip_contexto,
    )
    return gasto


def resumen_financiero(*, desde=None, hasta=None):
    from apps.compras.models import Compra, PagoCompra
    from apps.ventas.models import PagoVenta, Venta

    pagos_venta = PagoVenta.objects.filter(estado="CONFIRMADO", venta__estado__in=["PAGADA", "PARCIAL", "PENDIENTE"])
    pagos_compra = PagoCompra.objects.filter(estado="CONFIRMADO", compra__estado__in=["PENDIENTE", "RECIBIDA"])
    gastos = Gasto.objects.filter(estado="REGISTRADO")
    if desde:
        pagos_venta = pagos_venta.filter(fecha_pago__date__gte=desde)
        pagos_compra = pagos_compra.filter(fecha_pago__date__gte=desde)
        gastos = gastos.filter(fecha_gasto__date__gte=desde)
    if hasta:
        pagos_venta = pagos_venta.filter(fecha_pago__date__lte=hasta)
        pagos_compra = pagos_compra.filter(fecha_pago__date__lte=hasta)
        gastos = gastos.filter(fecha_gasto__date__lte=hasta)
    ingreso_ventas = pagos_venta.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    egreso_compras = pagos_compra.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    egreso_gastos = gastos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    ventas_deuda = Venta.objects.exclude(estado="ANULADA")
    compras_deuda = Compra.objects.exclude(estado="ANULADA")
    por_cobrar = sum((venta.saldo_pendiente for venta in ventas_deuda), Decimal("0.00"))
    por_pagar = sum((compra.saldo_pendiente for compra in compras_deuda), Decimal("0.00"))
    egresos = egreso_compras + egreso_gastos
    return {
        "ingresos_ventas": ingreso_ventas.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "egresos_compras": egreso_compras.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "egresos_gastos": egreso_gastos.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "egresos": egresos.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "utilidad": (ingreso_ventas - egresos).quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "por_cobrar": por_cobrar.quantize(CENTAVO, rounding=ROUND_HALF_UP),
        "por_pagar": por_pagar.quantize(CENTAVO, rounding=ROUND_HALF_UP),
    }
