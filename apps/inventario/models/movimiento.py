from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

class MovimientoInventario(models.Model):
    TIPOS = [(x, x.replace("_", " ").title()) for x in ["ENTRADA", "SALIDA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO", "DEVOLUCION", "TRANSFERENCIA"]]
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT)
    almacen = models.ForeignKey("inventario.Almacen", on_delete=models.PROTECT)
    lote = models.ForeignKey("inventario.Lote", on_delete=models.PROTECT, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0.001)])
    motivo = models.CharField(max_length=255, blank=True)
    referencia_tipo = models.CharField(max_length=30, blank=True)
    referencia_id = models.PositiveBigIntegerField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "movimientos_inventario"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="chk_mov_inv_cantidad_gt_0",
            ),
        ]
        indexes = [
            models.Index(fields=["producto", "fecha"]),
            models.Index(fields=["referencia_tipo", "referencia_id"]),
        ]

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.producto} ({self.cantidad})"
