from django.db import models
from django.core.validators import MinValueValidator

class Lote(models.Model):
    ESTADOS = [
        ("DISPONIBLE", "Disponible"),
        ("AGOTADO", "Agotado"),
        ("VENCIDO", "Vencido"),
        ("CUARENTENA", "Cuarentena"),
    ]
    detalle_compra = models.ForeignKey("compras.DetalleCompra", on_delete=models.PROTECT, related_name="lotes")
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT, related_name="lotes")
    almacen = models.ForeignKey("inventario.Almacen", on_delete=models.PROTECT, related_name="lotes")
    codigo_lote = models.CharField(max_length=60)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField()
    cantidad_recibida = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    cantidad_disponible = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=ESTADOS, default="DISPONIBLE")

    class Meta:
        db_table = "lotes"
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "almacen", "codigo_lote"],
                name="uq_lote_producto_almacen_codigo",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_disponible__gte=0),
                name="chk_lote_cantidad_disponible_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_disponible__lte=models.F("cantidad_recibida")),
                name="chk_lote_cantidad_disponible_lte_recibida",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_recibida__gte=0),
                name="chk_lote_cantidad_recibida_gte_0",
            ),
        ]
        indexes = [
            models.Index(fields=["fecha_vencimiento"]),
            models.Index(fields=["producto", "estado"]),
            models.Index(fields=["producto", "almacen", "estado"]),
        ]

    def __str__(self):
        return f"{self.producto} - {self.codigo_lote} ({self.almacen})"
