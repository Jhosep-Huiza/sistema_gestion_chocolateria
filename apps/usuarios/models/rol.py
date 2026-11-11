from django.db import models
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "roles"
    def __str__(self): return self.nombre
