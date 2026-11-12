from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Almacen, Inventario, Lote
from apps.productos.models import Categoria, Producto
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Rol, Usuario
from .models import SecuenciaVenta, Venta
from .services import registrar_venta


class VentaConcurrenteTest(TransactionTestCase):
    """Comprueba el bloqueo del stock cuando dos ventas compiten por un lote."""

    reset_sequences = True

    def setUp(self):
        rol = Rol.objects.create(nombre="Vendedor")
        self.usuario = Usuario.objects.create_user(username="vendedor_concurrente", password="pass", rol=rol)
        categoria = Categoria.objects.create(nombre="Chocolate concurrente")
        self.producto = Producto.objects.create(
            categoria=categoria, codigo="CONC-01", nombre="Bombón concurrente",
            precio_compra_referencial=Decimal("2.00"), precio_venta=Decimal("5.00"),
        )
        self.almacen = Almacen.objects.create(nombre="Almacén concurrencia")
        proveedor = Proveedor.objects.create(razon_social="Proveedor concurrencia", ruc="20999111222")
        compra = Compra.objects.create(
            proveedor=proveedor, usuario=self.usuario, numero_compra="COMP-CONC-1",
            tipo_documento="FACTURA", fecha_compra=timezone.now(),
        )
        detalle_compra = DetalleCompra.objects.create(
            compra=compra, producto=self.producto, cantidad=Decimal("1.000"),
            precio_unitario=Decimal("2.00"), subtotal=Decimal("2.00"),
        )
        self.inventario = Inventario.objects.create(
            producto=self.producto, almacen=self.almacen, stock_actual=Decimal("1.000"),
        )
        self.lote = Lote.objects.create(
            detalle_compra=detalle_compra, producto=self.producto, almacen=self.almacen,
            codigo_lote="CONC-LOTE-1", fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("1.000"), cantidad_disponible=Decimal("1.000"),
        )
        # Evita que la creación inicial de la secuencia compita con el bloqueo del lote.
        SecuenciaVenta.objects.update_or_create(pk=1, defaults={"ultimo_numero": 0})

    @skipUnlessDBFeature("has_select_for_update")
    def test_dos_ventas_simultaneas_no_dejan_stock_negativo(self):
        barrera = Barrier(2)

        def vender():
            close_old_connections()
            try:
                barrera.wait(timeout=10)
                venta = registrar_venta(
                    usuario=self.usuario, almacen_id=self.almacen.pk,
                    lineas=[{
                        "producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                        "precio_unitario": Decimal("5.00"),
                    }],
                )
                return ("ok", venta.pk)
            except ValidationError:
                return ("sin_stock", None)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            resultados = list(ejecutor.map(lambda _: vender(), range(2)))

        self.assertEqual([estado for estado, _ in resultados].count("ok"), 1)
        self.assertEqual([estado for estado, _ in resultados].count("sin_stock"), 1)
        self.inventario.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.inventario.stock_actual, Decimal("0.000"))
        self.assertEqual(self.lote.cantidad_disponible, Decimal("0.000"))
        self.assertEqual(Venta.objects.count(), 1)
