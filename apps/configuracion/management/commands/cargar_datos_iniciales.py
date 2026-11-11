from django.core.management.base import BaseCommand
from apps.usuarios.models import Rol
from apps.productos.models import Categoria
from apps.configuracion.models import MetodoPago
from apps.configuracion.models import Configuracion
from apps.inventario.models import Almacen
from apps.productos.models import Marca, Producto

class Command(BaseCommand):
    help = "Carga de forma idempotente los datos iniciales de ChocoGest."

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
        almacen, _ = Almacen.objects.get_or_create(
            nombre="Almacén principal",
            defaults={"ubicacion": "Principal", "descripcion": "Almacén principal de ChocoGest."},
        )
        configuracion = Configuracion.objects.order_by("pk").first()
        if configuracion is None:
            Configuracion.objects.create(
                nombre_negocio="ChocoGest", porcentaje_igv="18.00", moneda="PEN",
            )
        marcas = {}
        for nombre in ["ChocoGest Artesanal", "Cacao del Valle"]:
            marcas[nombre], _ = Marca.objects.get_or_create(nombre=nombre)

        muestras = [
            ("Tabletas", "CHOCO-70", "Tableta de chocolate 70% cacao", "12.00", "4.50", "ChocoGest Artesanal"),
            ("Bombones", "BOMB-CLAS", "Bombones surtidos clásicos", "24.00", "9.00", "ChocoGest Artesanal"),
            ("Trufas", "TRUF-CAC", "Trufas de cacao", "18.00", "6.50", "Cacao del Valle"),
        ]
        categorias = {categoria.nombre: categoria for categoria in Categoria.objects.filter(nombre__in=[m[0] for m in muestras])}
        for categoria_nombre, codigo, nombre, precio, costo, marca_nombre in muestras:
            Producto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "categoria": categorias[categoria_nombre],
                    "marca": marcas[marca_nombre],
                    "nombre": nombre,
                    "precio_venta": precio,
                    "precio_compra_referencial": costo,
                },
            )
        self.stdout.write(self.style.SUCCESS("Datos iniciales de ChocoGest cargados correctamente."))
