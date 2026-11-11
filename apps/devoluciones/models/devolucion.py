from django.conf import settings
from django.db import models
class Devolucion(models.Model):
    ESTADOS = [("PENDIENTE","Pendiente"),("APROBADA","Aprobada"),("RECHAZADA","Rechazada")]
    TIPOS = [("REEMBOLSO","Reembolso"),("CAMBIO","Cambio"),("NOTA_CREDITO","Nota de crédito")]
    venta = models.ForeignKey("ventas.Venta", on_delete=models.PROTECT, related_name="devoluciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_devolucion = models.DateTimeField()
    motivo = models.TextField()
    tipo_reembolso = models.CharField(max_length=30, choices=TIPOS)
    total_devolucion = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")
    class Meta: db_table = "devoluciones"
