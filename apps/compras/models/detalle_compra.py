from django.db import models
class DetalleCompra(models.Model):
    compra = models.ForeignKey("compras.Compra", on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta: db_table = "detalle_compras"
