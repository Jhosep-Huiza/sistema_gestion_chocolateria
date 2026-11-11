from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.db.utils import IntegrityError
from apps.productos.models import Categoria, Producto
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra
from apps.usuarios.models import Rol, Usuario

class InventarioBaseModelosTest(TestCase):
    """Pruebas de modelos y restricciones de inventario (Fase 0)."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Almacenero", descripcion="Almacén")
        self.usuario = Usuario.objects.create_user(
            username="almacen1", password="password123", rol=self.rol
        )
        self.categoria = Categoria.objects.create(nombre="Chocolates")
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            codigo="CHOC-001",
            nombre="Chocolate Oscuro 70%",
            precio_compra_referencial=Decimal("5.00"),
            precio_venta=Decimal("10.00"),
        )
        self.almacen1 = Almacen.objects.create(nombre="Almacén Central")
        self.almacen2 = Almacen.objects.create(nombre="Almacén Secundario")
        self.proveedor = Proveedor.objects.create(razon_social="Cacao del Perú SAC", ruc="20123456789")
        self.compra = Compra.objects.create(
            proveedor=self.proveedor,
            usuario=self.usuario,
            numero_compra="COM-001",
            tipo_documento="FACTURA",
            fecha_compra=timezone.now(),
        )
        self.detalle_compra = DetalleCompra.objects.create(
            compra=self.compra,
            producto=self.producto,
            cantidad=Decimal("10.000"),
            precio_unitario=Decimal("5.00"),
            subtotal=Decimal("50.00"),
        )

    def test_lote_con_almacen_y_restriccion_unica(self):
        """Verifica que Lote requiera almacén y la unicidad sea (producto, almacen, codigo_lote)."""
        lote1 = Lote.objects.create(
            detalle_compra=self.detalle_compra,
            producto=self.producto,
            almacen=self.almacen1,
            codigo_lote="LOT-001",
            fecha_vencimiento=timezone.localdate() + timedelta(days=90),
            cantidad_recibida=Decimal("10.000"),
            cantidad_disponible=Decimal("10.000"),
        )
        self.assertEqual(lote1.almacen, self.almacen1)

        # Mismo código de lote pero en diferente almacén debe permitirse
        lote_otro_almacen = Lote.objects.create(
            detalle_compra=self.detalle_compra,
            producto=self.producto,
            almacen=self.almacen2,
            codigo_lote="LOT-001",
            fecha_vencimiento=timezone.localdate() + timedelta(days=90),
            cantidad_recibida=Decimal("5.000"),
            cantidad_disponible=Decimal("5.000"),
        )
        self.assertIsNotNone(lote_otro_almacen.pk)

        # Mismo código en el mismo almacén y producto debe fallar por unicidad
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Lote.objects.create(
                    detalle_compra=self.detalle_compra,
                    producto=self.producto,
                    almacen=self.almacen1,
                    codigo_lote="LOT-001",
                    fecha_vencimiento=timezone.localdate() + timedelta(days=90),
                    cantidad_recibida=Decimal("10.000"),
                    cantidad_disponible=Decimal("10.000"),
                )

    def test_check_constraint_inventario_stock_negativo(self):
        """Valida que Inventario rechace stock_actual < 0."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Inventario.objects.create(
                    producto=self.producto,
                    almacen=self.almacen1,
                    stock_actual=Decimal("-1.000"),
                    stock_reservado=Decimal("0.000"),
                )

    def test_check_constraint_inventario_stock_reservado_excede_actual(self):
        """Valida que Inventario rechace stock_reservado > stock_actual."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Inventario.objects.create(
                    producto=self.producto,
                    almacen=self.almacen1,
                    stock_actual=Decimal("5.000"),
                    stock_reservado=Decimal("6.000"),
                )

    def test_check_constraint_lote_disponible_excede_recibida(self):
        """Valida que Lote rechace cantidad_disponible > cantidad_recibida."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Lote.objects.create(
                    detalle_compra=self.detalle_compra,
                    producto=self.producto,
                    almacen=self.almacen1,
                    codigo_lote="LOT-CHK-1",
                    fecha_vencimiento=timezone.localdate() + timedelta(days=90),
                    cantidad_recibida=Decimal("10.000"),
                    cantidad_disponible=Decimal("12.000"),
                )

    def test_check_constraint_lote_disponible_negativo(self):
        """Valida que Lote rechace cantidad_disponible < 0."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Lote.objects.create(
                    detalle_compra=self.detalle_compra,
                    producto=self.producto,
                    almacen=self.almacen1,
                    codigo_lote="LOT-CHK-2",
                    fecha_vencimiento=timezone.localdate() + timedelta(days=90),
                    cantidad_recibida=Decimal("10.000"),
                    cantidad_disponible=Decimal("-1.000"),
                )
