from django.db import models
class Almacen(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "almacenes"
    def __str__(self): return self.nombre
