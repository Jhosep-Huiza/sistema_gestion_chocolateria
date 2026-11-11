from django.contrib.auth.models import AbstractUser
from django.db import models
class Usuario(AbstractUser):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    rol = models.ForeignKey("usuarios.Rol", on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios")
    REQUIRED_FIELDS = ["email", "nombres", "apellidos"]
    class Meta: db_table = "usuarios"
    def __str__(self): return f"{self.nombres} {self.apellidos}"

    @property
    def es_administrador(self):
        return self.is_superuser or (self.rol is not None and self.rol.nombre == "Administrador")

    @property
    def es_vendedor(self):
        return self.es_administrador or (self.rol is not None and self.rol.nombre == "Vendedor")

    @property
    def es_cajero(self):
        return self.es_administrador or (self.rol is not None and self.rol.nombre == "Cajero")

    @property
    def es_almacenero(self):
        return self.es_administrador or (self.rol is not None and self.rol.nombre == "Almacenero")
