from django.db import models
from django.core.validators import MinValueValidator
class Producto(models.Model):
    categoria = models.ForeignKey("productos.Categoria", on_delete=models.PROTECT, related_name="productos")
    marca = models.ForeignKey("productos.Marca", on_delete=models.SET_NULL, null=True, blank=True, related_name="productos")
    codigo = models.CharField(max_length=50, unique=True)
    codigo_barras = models.CharField(max_length=100, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    peso_gramos = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    precio_compra_referencial = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)
    estado = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: db_table = "productos"; ordering = ["nombre"]
    def __str__(self): return f"{self.codigo} - {self.nombre}"
