from django.conf import settings
from django.db import models
class Auditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=100)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.PositiveBigIntegerField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "auditoria"
        ordering = ["-fecha"]
