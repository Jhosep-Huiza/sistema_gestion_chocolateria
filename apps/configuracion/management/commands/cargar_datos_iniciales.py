from django.core.management.base import BaseCommand
from apps.usuarios.models import Rol
from apps.productos.models import Categoria
from apps.configuracion.models import MetodoPago

class Command(BaseCommand):
    help = "Carga roles, categorías y métodos de pago iniciales de ChocoGest."

    def handle(self, *args, **options):
        for nombre, descripcion in [
            ("Administrador","Acceso completo al sistema"),
            ("Vendedor","Gestión de ventas y clientes"),
            ("Cajero","Apertura, cierre y movimientos de caja"),
            ("Almacenero","Gestión de compras e inventario"),
        ]:
            Rol.objects.get_or_create(nombre=nombre, defaults={"descripcion":descripcion})
        for nombre in ["Tabletas","Bombones","Trufas","Chocolates amargos","Chocolates con leche","Regalos"]:
            Categoria.objects.get_or_create(nombre=nombre)
        for nombre in ["Efectivo","Yape","Plin","Tarjeta","Transferencia bancaria"]:
            MetodoPago.objects.get_or_create(nombre=nombre)
        self.stdout.write(self.style.SUCCESS("Datos iniciales de ChocoGest cargados correctamente."))
