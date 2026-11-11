from django.db import models
class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "metodos_pago"
    def __str__(self): return self.nombre
