from django.db import models


class SecuenciaVenta(models.Model):
    """Contador bloqueable que conserva la numeración correlativa de ventas."""
    ultimo_numero = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = "secuencia_ventas"

    def __str__(self):
        return f"Secuencia de ventas: {self.ultimo_numero}"
