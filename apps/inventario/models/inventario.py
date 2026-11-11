from django.db import models
from django.core.validators import MinValueValidator

class Inventario(models.Model):
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT, related_name="existencias")
    almacen = models.ForeignKey("inventario.Almacen", on_delete=models.PROTECT, related_name="existencias")
    stock_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    stock_reservado = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventario"
        constraints = [
            models.UniqueConstraint(fields=["producto", "almacen"], name="uq_inventario_producto_almacen"),
            models.CheckConstraint(
                condition=models.Q(stock_actual__gte=0),
                name="chk_inventario_stock_actual_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_reservado__gte=0),
                name="chk_inventario_stock_reservado_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_reservado__lte=models.F("stock_actual")),
                name="chk_inventario_stock_reservado_lte_stock_actual",
            ),
        ]

    def __str__(self):
        return f"{self.producto} / {self.almacen}"
