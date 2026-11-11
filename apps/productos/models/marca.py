from django.db import models
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "marcas"
    def __str__(self): return self.nombre
