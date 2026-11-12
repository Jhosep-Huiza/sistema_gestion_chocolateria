from django.conf import settings
from django.db import models

class Gasto(models.Model):
    ESTADOS = [("REGISTRADO", "Registrado"), ("ANULADO", "Anulado")]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    caja = models.ForeignKey("caja.Caja", on_delete=models.PROTECT, null=True, blank=True, related_name="gastos")
    categoria = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    es_efectivo = models.BooleanField(default=False)
    fecha_gasto = models.DateTimeField()
    comprobante = models.FileField(upload_to="gastos/", blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="REGISTRADO")

    class Meta:
        db_table = "gastos"
        ordering = ["-fecha_gasto"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gte=0),
                name="chk_gasto_monto_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.categoria} - {self.monto}"
