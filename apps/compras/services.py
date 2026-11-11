from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.compras.models import Compra
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.usuarios.services import registrar_auditoria

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
        total_lotes = sum((item["cantidad"] for item in lotes_data), start=0)
        if total_lotes != detalle.cantidad:
            raise ValidationError(
                f"Las cantidades de los lotes de {detalle.producto} deben sumar {detalle.cantidad}."
            )

        for item in lotes_data:
            vencimiento = item["fecha_vencimiento"]
            if vencimiento <= timezone.localdate():
                raise ValidationError("No se puede recibir un lote vencido.")
            lote = Lote.objects.create(
                detalle_compra=detalle,
                producto=detalle.producto,
                almacen=almacen,
                codigo_lote=item["codigo_lote"],
                fecha_fabricacion=item.get("fecha_fabricacion"),
                fecha_vencimiento=vencimiento,
                cantidad_recibida=item["cantidad"],
                cantidad_disponible=item["cantidad"],
                estado="DISPONIBLE",
            )
            existencia, _ = Inventario.objects.select_for_update().get_or_create(
                producto=detalle.producto, almacen=almacen,
                defaults={"stock_actual": 0, "stock_reservado": 0},
            )
            existencia = Inventario.objects.select_for_update().get(pk=existencia.pk)
            existencia.stock_actual += item["cantidad"]
            existencia.save(update_fields=["stock_actual", "updated_at"])
            MovimientoInventario.objects.create(
                producto=detalle.producto, almacen=almacen, lote=lote,
                usuario=usuario, tipo_movimiento="ENTRADA",
                cantidad=item["cantidad"], motivo=f"Recepción de compra {compra.numero_compra}",
                referencia_tipo="COMPRA", referencia_id=compra.pk,
            )

    compra.estado = "RECIBIDA"
    compra.save(update_fields=["estado"])
    registrar_auditoria(
        usuario=usuario, accion="RECEPCION_COMPRA_STOCK", tabla_afectada="inventario",
        registro_id=compra.pk, descripcion=f"Recepción de compra {compra.numero_compra} en {almacen}.",
        direccion_ip=direccion_ip,
    )
    return compra
