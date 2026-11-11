from django.db import models
class DetalleDevolucion(models.Model):
    ESTADOS_PRODUCTO = [("REINGRESAR","Reingresar"),("CUARENTENA","Cuarentena"),("DANADO","Dañado")]
    devolucion = models.ForeignKey("devoluciones.Devolucion", on_delete=models.CASCADE, related_name="detalles")
    detalle_venta = models.ForeignKey("ventas.DetalleVenta", on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    motivo = models.CharField(max_length=255, blank=True)
    estado_producto = models.CharField(max_length=30, choices=ESTADOS_PRODUCTO)
    class Meta: db_table = "detalle_devoluciones"
