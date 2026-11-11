from django.db import models
class Cliente(models.Model):
    TIPO_DOCUMENTO = [("DNI","DNI"),("RUC","RUC"),("CE","Carné de extranjería"),("OTRO","Otro")]
    tipo_documento = models.CharField(max_length=15, choices=TIPO_DOCUMENTO, blank=True)
    numero_documento = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nombres = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.BooleanField(default=True)
    class Meta: db_table = "clientes"; ordering = ["nombres"]
    def __str__(self): return self.nombres
