from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.usuarios.services import contexto_auditoria, registrar_auditoria
from .models import Caja, MovimientoCaja

CENTAVO = Decimal("0.01")


def _importe(valor):
    try:
        importe = Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ValidationError("Ingresa un importe válido.") from error
    if importe < 0:
        raise ValidationError("El importe no puede ser negativo.")
    return importe


@transaction.atomic
def abrir_caja(*, usuario, monto_inicial):
    monto_inicial = _importe(monto_inicial)
    if Caja.objects.select_for_update().filter(usuario=usuario, estado="ABIERTA").exists():
        raise ValidationError("Ya tienes una caja abierta.")
    try:
        with transaction.atomic():
            return Caja.objects.create(
                usuario=usuario, fecha_apertura=timezone.now(), monto_inicial=monto_inicial,
                estado="ABIERTA",
            )
    except IntegrityError as error:
        raise ValidationError("Ya tienes una caja abierta.") from error


@transaction.atomic
def registrar_movimiento_caja(*, caja_id, usuario, tipo, concepto, monto):
    caja = Caja.objects.select_for_update().get(pk=caja_id)
    if caja.estado != "ABIERTA":
        raise ValidationError("La caja está cerrada y no admite movimientos.")
    if tipo not in {"INGRESO", "EGRESO"}:
        raise ValidationError("Selecciona ingreso o egreso.")
    concepto = (concepto or "").strip()
    if not concepto or len(concepto) > 150:
        raise ValidationError("El concepto es obligatorio y admite hasta 150 caracteres.")
    monto = _importe(monto)
    if monto <= 0:
        raise ValidationError("El monto debe ser mayor a cero.")
    return MovimientoCaja.objects.create(
        caja=caja, usuario=usuario, tipo=tipo, concepto=concepto, monto=monto,
        referencia_tipo="MANUAL",
    )


@transaction.atomic
def cerrar_caja(*, caja_id, usuario, monto_final, direccion_ip=None):
    caja = Caja.objects.select_for_update().get(pk=caja_id)
    if caja.estado != "ABIERTA":
        raise ValidationError("La caja ya está cerrada.")
    monto_final = _importe(monto_final)
    totales = caja.movimientos.aggregate(
        ingresos=Sum("monto", filter=Q(tipo="INGRESO")),
        egresos=Sum("monto", filter=Q(tipo="EGRESO")),
    )
    esperado = caja.monto_inicial + (totales["ingresos"] or Decimal("0.00")) - (totales["egresos"] or Decimal("0.00"))
    caja.monto_esperado = esperado.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    caja.monto_final = monto_final
    caja.diferencia = (monto_final - caja.monto_esperado).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    caja.fecha_cierre = timezone.now()
    caja.estado = "CERRADA"
    caja.save(update_fields=["monto_esperado", "monto_final", "diferencia", "fecha_cierre", "estado"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="CIERRE_CAJA", tabla_afectada="cajas", registro_id=caja.pk,
        descripcion=f"Caja cerrada. Esperado S/ {caja.monto_esperado:.2f}, contado S/ {monto_final:.2f}, diferencia S/ {caja.diferencia:.2f}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return caja
