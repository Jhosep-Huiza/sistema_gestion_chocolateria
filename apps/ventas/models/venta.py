from django.conf import settings
from django.db import models
class Venta(models.Model):
    ESTADOS = [("PENDIENTE","Pendiente"),("PAGADA","Pagada"),("PARCIAL","Parcialmente pagada"),("ANULADA","Anulada")]
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, null=True, blank=True, related_name="ventas")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ventas")
    caja = models.ForeignKey("caja.Caja", on_delete=models.PROTECT, null=True, blank=True, related_name="ventas")
    numero_venta = models.CharField(max_length=50, unique=True)
    tipo_comprobante = models.CharField(max_length=30, default="TICKET")
    numero_comprobante = models.CharField(max_length=50, blank=True)
    fecha_venta = models.DateTimeField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")
    observaciones = models.TextField(blank=True)
    class Meta: db_table = "ventas"; ordering = ["-fecha_venta"]
    def __str__(self): return self.numero_venta
