from django.conf import settings
from django.db import models
from django.db.models import Sum
from decimal import Decimal
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

    @property
    def monto_pagado(self):
        return self.pagos.filter(estado="CONFIRMADO").aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return max(self.total - self.monto_pagado, Decimal("0.00"))

    @property
    def estado_pago(self):
        if self.saldo_pendiente == 0:
            return "PAGADA"
        if self.monto_pagado > 0:
            return "PARCIAL"
        return "PENDIENTE"
