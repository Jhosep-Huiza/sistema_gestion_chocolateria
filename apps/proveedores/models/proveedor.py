from django.db import models
class Proveedor(models.Model):
    ruc = models.CharField(max_length=11, unique=True, null=True, blank=True)
    razon_social = models.CharField(max_length=150)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "proveedores"; ordering = ["razon_social"]
    def __str__(self): return self.razon_social
