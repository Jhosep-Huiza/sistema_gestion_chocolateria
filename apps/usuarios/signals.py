from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from apps.usuarios.services import contexto_auditoria, registrar_auditoria
from apps.ventas.models import Venta
from apps.caja.models import Caja
from apps.inventario.models import MovimientoInventario


def _estado_anterior(sender, instance):
    if not instance.pk:
        return None
    return sender.objects.filter(pk=instance.pk).values_list("estado", flat=True).first()


@receiver(pre_save, sender=Venta)
def guardar_estado_anterior_venta(sender, instance, **kwargs):
    instance._estado_anterior_auditoria = _estado_anterior(sender, instance)


@receiver(post_save, sender=Venta)
def auditar_anulacion_venta(sender, instance, created, **kwargs):
    if instance.estado != "ANULADA" or (not created and instance._estado_anterior_auditoria == "ANULADA"):
        return
    _, ip = contexto_auditoria()
    registrar_auditoria(usuario=instance.usuario, accion="ANULACION_VENTA",
                        tabla_afectada="ventas", registro_id=instance.pk,
                        descripcion=f"Venta {instance.numero_venta} anulada.", direccion_ip=ip)


@receiver(pre_save, sender=Caja)
def guardar_estado_anterior_caja(sender, instance, **kwargs):
    instance._estado_anterior_auditoria = _estado_anterior(sender, instance)


@receiver(post_save, sender=Caja)
def auditar_cierre_caja(sender, instance, created, **kwargs):
    if instance.estado != "CERRADA" or (not created and instance._estado_anterior_auditoria == "CERRADA"):
        return
    _, ip = contexto_auditoria()
    registrar_auditoria(usuario=instance.usuario, accion="CIERRE_CAJA",
                        tabla_afectada="cajas", registro_id=instance.pk,
                        descripcion=f"Caja {instance.pk} cerrada.", direccion_ip=ip)


@receiver(post_save, sender=MovimientoInventario)
def auditar_ajuste_stock(sender, instance, created, **kwargs):
    if not created or not instance.tipo_movimiento.startswith("AJUSTE_"):
        return
    _, ip = contexto_auditoria()
    registrar_auditoria(usuario=instance.usuario, accion="AJUSTE_STOCK",
                        tabla_afectada="inventario", registro_id=instance.pk,
                        descripcion=(f"{instance.get_tipo_movimiento_display()}: {instance.cantidad} "
                                     f"de {instance.producto} en {instance.almacen}."),
                        direccion_ip=ip)
