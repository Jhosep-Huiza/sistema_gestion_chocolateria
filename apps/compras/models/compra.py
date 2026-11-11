from django.conf import settings
from django.db import models
class Compra(models.Model):
    ESTADOS = [("PENDIENTE","Pendiente"),("RECIBIDA","Recibida"),("ANULADA","Anulada")]
    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.PROTECT, related_name="compras")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras")
    numero_compra = models.CharField(max_length=50, unique=True)
    tipo_documento = models.CharField(max_length=30)
    numero_documento = models.CharField(max_length=50, blank=True)
    fecha_compra = models.DateTimeField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")
    observaciones = models.TextField(blank=True)
    class Meta: db_table = "compras"; ordering = ["-fecha_compra"]
    def __str__(self): return self.numero_compra
