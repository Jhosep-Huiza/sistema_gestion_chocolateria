from django.db import models
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to="categorias/", blank=True, null=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "categorias"; verbose_name_plural = "categorías"
    def __str__(self): return self.nombre
