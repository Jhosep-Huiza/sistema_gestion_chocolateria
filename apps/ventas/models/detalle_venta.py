from django.db import models
class DetalleVenta(models.Model):
    venta = models.ForeignKey("ventas.Venta", on_delete=models.PROTECT, related_name="detalles")
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT)
    lote = models.ForeignKey("inventario.Lote", on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad_reservada = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    class Meta: db_table = "detalle_ventas"
