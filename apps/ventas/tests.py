from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.productos.models import Categoria, Producto
from apps.inventario.models import Almacen, Inventario, Lote
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra
from apps.ventas.models import Venta, PagoVenta
from apps.configuracion.models import MetodoPago
from apps.usuarios.models import Rol, Usuario
from apps.ventas.services import registrar_venta

class VentasBaseTest(TestCase):
    """Pruebas de ventas y filtrado de lotes por almacén (Fase 0)."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Vendedor")
        self.usuario = Usuario.objects.create_user(
            username="vendedor_test", password="password123", rol=self.rol
        )
        self.categoria = Categoria.objects.create(nombre="Trufas")
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            codigo="TRUF-01",
            nombre="Trufa Clásica",
            precio_compra_referencial=Decimal("2.00"),
            precio_venta=Decimal("5.00"),
        )
        self.almacen_a = Almacen.objects.create(nombre="Tienda A")
        self.almacen_b = Almacen.objects.create(nombre="Tienda B")
        self.metodo_pago = MetodoPago.objects.create(nombre="Efectivo")

        self.proveedor = Proveedor.objects.create(razon_social="Proveedor Trufas", ruc="20111222333")
        self.compra = Compra.objects.create(
            proveedor=self.proveedor,
            usuario=self.usuario,
            numero_compra="COM-TRUF-01",
            tipo_documento="BOLETA",
            fecha_compra=timezone.now(),
        )
        self.detalle_compra = DetalleCompra.objects.create(
            compra=self.compra,
            producto=self.producto,
            cantidad=Decimal("50.000"),
            precio_unitario=Decimal("2.00"),
            subtotal=Decimal("100.00"),
        )

        # Lote en Almacén A (3 unidades)
        Inventario.objects.create(
            producto=self.producto,
            almacen=self.almacen_a,
            stock_actual=Decimal("3.000"),
            stock_reservado=Decimal("0.000"),
        )
        self.lote_a = Lote.objects.create(
            detalle_compra=self.detalle_compra,
            producto=self.producto,
            almacen=self.almacen_a,
            codigo_lote="LOTE-A",
            fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("3.000"),
            cantidad_disponible=Decimal("3.000"),
        )

        # Lote en Almacén B (20 unidades)
        Inventario.objects.create(
            producto=self.producto,
            almacen=self.almacen_b,
            stock_actual=Decimal("20.000"),
            stock_reservado=Decimal("0.000"),
        )
        self.lote_b = Lote.objects.create(
            detalle_compra=self.detalle_compra,
            producto=self.producto,
            almacen=self.almacen_b,
            codigo_lote="LOTE-B",
            fecha_vencimiento=timezone.localdate() + timedelta(days=20),
            cantidad_recibida=Decimal("20.000"),
            cantidad_disponible=Decimal("20.000"),
        )

    def test_registrar_venta_filtra_lotes_por_almacen_elegido(self):
        """Verifica que registrar_venta descuente únicamente lotes del almacén seleccionado."""
        # Vendemos 2 unidades desde Tienda A
        lineas = [{
            "producto_id": self.producto.pk,
            "cantidad": Decimal("2.000"),
            "precio_unitario": Decimal("5.00"),
        }]
        venta = registrar_venta(
            usuario=self.usuario,
            almacen_id=self.almacen_a.pk,
            lineas=lineas,
            numero_venta="V-TEST-001",
        )
        self.assertEqual(venta.total, Decimal("10.00"))

        # Verificamos que el lote A se descontó (queda 1)
        self.lote_a.refresh_from_db()
        self.assertEqual(self.lote_a.cantidad_disponible, Decimal("1.000"))

        # Verificamos que el lote B quedó intacto (sigue 20)
        self.lote_b.refresh_from_db()
        self.assertEqual(self.lote_b.cantidad_disponible, Decimal("20.000"))

    def test_registrar_venta_falla_si_almacen_no_tiene_lotes_suficientes(self):
        """Si Tienda A solo tiene 3, pedir 5 debe fallar aunque Tienda B tenga stock."""
        lineas = [{
            "producto_id": self.producto.pk,
            "cantidad": Decimal("5.000"),
            "precio_unitario": Decimal("5.00"),
        }]
        with self.assertRaises(ValidationError):
            registrar_venta(
                usuario=self.usuario,
                almacen_id=self.almacen_a.pk,
                lineas=lineas,
                numero_venta="V-TEST-002",
            )

    def test_pago_venta_monto_check_constraint(self):
        """Verifica que PagoVenta impida montos negativos mediante CheckConstraint."""
        from django.db import transaction
        venta = Venta.objects.create(
            usuario=self.usuario,
            numero_venta="V-PAGO-001",
            tipo_comprobante="TICKET",
            fecha_venta=timezone.now(),
            total=Decimal("50.00"),
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PagoVenta.objects.create(
                    venta=venta,
                    metodo_pago=self.metodo_pago,
                    usuario=self.usuario,
                    monto=Decimal("-5.00"),
                    fecha_pago=timezone.now(),
                )
