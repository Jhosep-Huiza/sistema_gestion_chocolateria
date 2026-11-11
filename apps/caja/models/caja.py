from django.conf import settings
from django.db import models

class Caja(models.Model):
    ESTADOS = [("ABIERTA", "Abierta"), ("CERRADA", "Cerrada")]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cajas")
    fecha_apertura = models.DateTimeField()
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    monto_final = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    monto_esperado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="ABIERTA")

    class Meta:
        db_table = "cajas"
        ordering = ["-fecha_apertura"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                condition=models.Q(estado="ABIERTA"),
                name="uq_caja_abierta_por_usuario",
            ),
            models.CheckConstraint(
                condition=models.Q(monto_inicial__gte=0),
                name="chk_caja_monto_inicial_gte_0",
            ),
        ]

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        if self.estado == "ABIERTA" and self.usuario_id:
            qs = Caja.objects.filter(usuario=self.usuario, estado="ABIERTA")
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({"usuario": "El usuario ya tiene una caja abierta."})

    def __str__(self):
        return f"Caja {self.id} - {self.usuario} ({self.estado})"
