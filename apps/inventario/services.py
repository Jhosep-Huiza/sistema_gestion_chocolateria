from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from apps.usuarios.services import contexto_auditoria, registrar_auditoria
from .models import Almacen, Inventario, Lote, MovimientoInventario

CANTIDAD_MINIMA = Decimal("0.001")


def _cantidad_positiva(valor):
    try:
        cantidad = Decimal(str(valor))
    except (TypeError, ValueError, ArithmeticError) as error:
        raise ValidationError("Ingresa una cantidad válida.") from error
    if cantidad <= 0 or cantidad.quantize(CANTIDAD_MINIMA) != cantidad:
        raise ValidationError("La cantidad debe ser mayor a cero y admitir hasta tres decimales.")
    return cantidad


def _motivo_obligatorio(motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo es obligatorio.")
    if len(motivo) > 255:
        raise ValidationError("El motivo no puede exceder 255 caracteres.")
    return motivo


@transaction.atomic
def ajustar_inventario(*, lote_id, cantidad, tipo, motivo, usuario, direccion_ip=None):
    """Ajusta existencias por conteo, actualizando lote, stock y kardex bajo bloqueo."""
    cantidad = _cantidad_positiva(cantidad)
    motivo = _motivo_obligatorio(motivo)
    if tipo not in {"POSITIVO", "NEGATIVO"}:
        raise ValidationError("El ajuste debe ser positivo o negativo.")

    lote = Lote.objects.select_for_update().select_related("producto", "almacen").get(pk=lote_id)
    inventario = Inventario.objects.select_for_update().filter(
        producto_id=lote.producto_id, almacen_id=lote.almacen_id,
    ).first()
    if not inventario:
        raise ValidationError("No existe una fila de inventario para el lote seleccionado.")

    if tipo == "POSITIVO":
        if lote.estado in {"CUARENTENA", "VENCIDO"} or lote.fecha_vencimiento < timezone.localdate():
            raise ValidationError("No se puede aumentar stock en un lote en cuarentena o vencido.")
        lote.cantidad_recibida += cantidad
        lote.cantidad_disponible += cantidad
        if lote.estado == "AGOTADO":
            lote.estado = "DISPONIBLE"
        tipo_movimiento = "AJUSTE_POSITIVO"
    else:
        if lote.cantidad_disponible < cantidad:
            raise ValidationError("El ajuste supera la cantidad disponible del lote.")
        if inventario.stock_actual - inventario.stock_reservado < cantidad:
            raise ValidationError("El stock está reservado y no admite este ajuste negativo.")
        lote.cantidad_disponible -= cantidad
        if lote.cantidad_disponible == 0:
            lote.estado = "AGOTADO"
        tipo_movimiento = "AJUSTE_NEGATIVO"

    inventario.stock_actual += cantidad if tipo == "POSITIVO" else -cantidad
    inventario.save(update_fields=["stock_actual", "updated_at"])
    lote.save(update_fields=["cantidad_recibida", "cantidad_disponible", "estado"])
    movimiento = MovimientoInventario.objects.create(
        producto=lote.producto, almacen=lote.almacen, lote=lote, usuario=usuario,
        tipo_movimiento=tipo_movimiento, cantidad=cantidad, motivo=motivo,
        referencia_tipo="AJUSTE",
    )
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="AJUSTE_STOCK", tabla_afectada="inventario",
        registro_id=movimiento.pk,
        descripcion=f"Ajuste {tipo.lower()} de {cantidad} unidades. Motivo: {motivo}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return movimiento


@transaction.atomic
def transferir_stock(*, lote_id, almacen_destino_id, cantidad, motivo, usuario, direccion_ip=None):
    """Transfiere una cantidad de lote entre almacenes y genera salida y entrada."""
    cantidad = _cantidad_positiva(cantidad)
    motivo = _motivo_obligatorio(motivo)
    lote_origen = Lote.objects.select_for_update().select_related("producto", "almacen", "detalle_compra").get(pk=lote_id)
    destino = Almacen.objects.get(pk=almacen_destino_id, estado=True)
    if destino.pk == lote_origen.almacen_id:
        raise ValidationError("El almacén de destino debe ser distinto al de origen.")
    if lote_origen.estado != "DISPONIBLE" or lote_origen.fecha_vencimiento < timezone.localdate():
        raise ValidationError("Solo se puede transferir stock de lotes disponibles y vigentes.")
    if cantidad > lote_origen.cantidad_disponible:
        raise ValidationError("La transferencia supera la cantidad disponible del lote.")

    origen_stock = Inventario.objects.select_for_update().filter(
        producto_id=lote_origen.producto_id, almacen_id=lote_origen.almacen_id,
    ).first()
    if not origen_stock or origen_stock.stock_actual - origen_stock.stock_reservado < cantidad:
        raise ValidationError("El stock del almacén de origen está reservado o es insuficiente.")
    destino_stock, _ = Inventario.objects.select_for_update().get_or_create(
        producto_id=lote_origen.producto_id, almacen=destino,
        defaults={"stock_actual": Decimal("0.000"), "stock_reservado": Decimal("0.000")},
    )
    destino_stock = Inventario.objects.select_for_update().get(pk=destino_stock.pk)

    lote_destino = Lote.objects.select_for_update().filter(
        producto_id=lote_origen.producto_id, almacen=destino,
        codigo_lote=lote_origen.codigo_lote,
    ).first()
    if lote_destino:
        if lote_destino.detalle_compra_id != lote_origen.detalle_compra_id:
            raise ValidationError("Ya existe en destino un lote con ese código de otro origen.")
        if lote_destino.estado != "DISPONIBLE":
            raise ValidationError("El lote existente en destino no está disponible para recibir stock.")
        lote_destino.cantidad_recibida += cantidad
        lote_destino.cantidad_disponible += cantidad
    else:
        lote_destino = Lote.objects.create(
            detalle_compra=lote_origen.detalle_compra,
            producto=lote_origen.producto, almacen=destino,
            codigo_lote=lote_origen.codigo_lote,
            fecha_fabricacion=lote_origen.fecha_fabricacion,
            fecha_vencimiento=lote_origen.fecha_vencimiento,
            cantidad_recibida=cantidad, cantidad_disponible=cantidad,
            estado="DISPONIBLE",
        )

    lote_origen.cantidad_disponible -= cantidad
    if lote_origen.cantidad_disponible == 0:
        lote_origen.estado = "AGOTADO"
    lote_origen.save(update_fields=["cantidad_disponible", "estado"])
    lote_destino.save(update_fields=["cantidad_recibida", "cantidad_disponible"])
    origen_stock.stock_actual -= cantidad
    origen_stock.save(update_fields=["stock_actual", "updated_at"])
    destino_stock.stock_actual += cantidad
    destino_stock.save(update_fields=["stock_actual", "updated_at"])

    salida = MovimientoInventario.objects.create(
        producto=lote_origen.producto, almacen=lote_origen.almacen, lote=lote_origen,
        usuario=usuario, tipo_movimiento="SALIDA", cantidad=cantidad,
        motivo=f"Transferencia a {destino.nombre}: {motivo}", referencia_tipo="TRANSFERENCIA",
    )
    entrada = MovimientoInventario.objects.create(
        producto=lote_destino.producto, almacen=destino, lote=lote_destino,
        usuario=usuario, tipo_movimiento="ENTRADA", cantidad=cantidad,
        motivo=f"Transferencia desde {lote_origen.almacen.nombre}: {motivo}",
        referencia_tipo="TRANSFERENCIA", referencia_id=salida.pk,
    )
    salida.referencia_id = entrada.pk
    salida.save(update_fields=["referencia_id"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="TRANSFERENCIA_STOCK", tabla_afectada="inventario",
        registro_id=salida.pk,
        descripcion=f"Transferencia de {cantidad} unidades de {lote_origen.almacen} a {destino}. Motivo: {motivo}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return salida, entrada


@transaction.atomic
def cambiar_estado_lote(*, lote_id, estado, usuario, direccion_ip=None):
    """Mueve un lote disponible a cuarentena o lo libera si aún es vigente."""
    if estado not in {"CUARENTENA", "DISPONIBLE"}:
        raise ValidationError("Solo se permite cambiar entre disponible y cuarentena.")
    lote = Lote.objects.select_for_update().get(pk=lote_id)
    if lote.estado not in {"DISPONIBLE", "CUARENTENA"}:
        raise ValidationError("Un lote agotado o vencido no puede cambiar de estado.")
    if estado == "DISPONIBLE":
        if lote.fecha_vencimiento < timezone.localdate():
            raise ValidationError("No se puede liberar un lote vencido.")
        if lote.cantidad_disponible <= 0:
            raise ValidationError("No se puede liberar un lote sin stock disponible.")
    anterior = lote.estado
    if anterior == estado:
        raise ValidationError("El lote ya tiene ese estado.")
    lote.estado = estado
    lote.save(update_fields=["estado"])
    _, ip_contexto = contexto_auditoria()
    registrar_auditoria(
        usuario=usuario, accion="CAMBIO_ESTADO_LOTE", tabla_afectada="lotes",
        registro_id=lote.pk,
        descripcion=f"Lote {lote.codigo_lote}: {anterior} → {estado}.",
        direccion_ip=direccion_ip or ip_contexto,
    )
    return lote


@transaction.atomic
def marcar_lotes_vencidos(*, hoy=None, usuario_sistema=None):
    """Marca vencidos, retira su cantidad activa de stock y crea movimientos."""
    hoy = hoy or timezone.localdate()
    ids = list(Lote.objects.filter(fecha_vencimiento__lt=hoy).exclude(estado="VENCIDO").values_list("pk", flat=True))
    marcados = 0
    movimientos = 0
    for lote_id in ids:
        lote = Lote.objects.select_for_update().select_related("producto", "almacen").get(pk=lote_id)
        if lote.fecha_vencimiento >= hoy or lote.estado == "VENCIDO":
            continue
        cantidad = lote.cantidad_disponible
        if cantidad > 0:
            inventario = Inventario.objects.select_for_update().filter(
                producto_id=lote.producto_id, almacen_id=lote.almacen_id,
            ).first()
            if not inventario or inventario.stock_actual < cantidad:
                raise ValidationError(f"No se pudo ajustar el stock vencido del lote {lote.codigo_lote}.")
            inventario.stock_actual -= cantidad
            inventario.stock_reservado = max(inventario.stock_reservado - cantidad, Decimal("0.000"))
            inventario.save(update_fields=["stock_actual", "stock_reservado", "updated_at"])
            lote.cantidad_disponible = Decimal("0.000")
            MovimientoInventario.objects.create(
                producto=lote.producto, almacen=lote.almacen, lote=lote,
                usuario=usuario_sistema or lote.detalle_compra.compra.usuario,
                tipo_movimiento="AJUSTE_NEGATIVO", cantidad=cantidad,
                motivo=f"Retiro por vencimiento ({lote.fecha_vencimiento:%d/%m/%Y})",
                referencia_tipo="VENCIMIENTO", referencia_id=lote.pk,
            )
            movimientos += 1
        lote.estado = "VENCIDO"
        lote.save(update_fields=["cantidad_disponible", "estado"])
        marcados += 1
    return {"marcados": marcados, "movimientos": movimientos}
