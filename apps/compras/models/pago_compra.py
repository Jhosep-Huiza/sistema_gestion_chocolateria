from django.conf import settings
from django.db import models

class PagoCompra(models.Model):
    ESTADOS = [("CONFIRMADO", "Confirmado"), ("ANULADO", "Anulado")]
    compra = models.ForeignKey("compras.Compra", on_delete=models.PROTECT, related_name="pagos")
    metodo_pago = models.ForeignKey("configuracion.MetodoPago", on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_pago = models.DateTimeField()
    referencia = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="CONFIRMADO")

    class Meta:
        db_table = "pagos_compras"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gte=0),
                name="chk_pago_compra_monto_gte_0",
            ),
        ]

    def __str__(self):
        return f"Pago Compra {self.compra_id} - {self.monto}"
