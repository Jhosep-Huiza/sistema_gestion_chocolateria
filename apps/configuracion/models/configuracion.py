from django.db import models
class Configuracion(models.Model):
    nombre_negocio = models.CharField(max_length=150)
    ruc = models.CharField(max_length=11, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to="configuracion/", blank=True, null=True)
    porcentaje_igv = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    moneda = models.CharField(max_length=10, default="PEN")
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: db_table = "configuracion"
    def __str__(self): return self.nombre_negocio
