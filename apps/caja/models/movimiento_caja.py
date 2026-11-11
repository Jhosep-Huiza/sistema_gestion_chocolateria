from django.conf import settings
from django.db import models

class MovimientoCaja(models.Model):
    TIPOS = [("INGRESO", "Ingreso"), ("EGRESO", "Egreso")]
    caja = models.ForeignKey("caja.Caja", on_delete=models.PROTECT, related_name="movimientos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    concepto = models.CharField(max_length=150)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    referencia_tipo = models.CharField(max_length=30, blank=True)
    referencia_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "movimientos_caja"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gte=0),
                name="chk_movimiento_caja_monto_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} - {self.concepto} ({self.monto})"
