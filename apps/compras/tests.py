from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.db.utils import IntegrityError
from apps.productos.models import Categoria, Producto
from apps.inventario.models import Almacen, Lote
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra, PagoCompra
from apps.configuracion.models import MetodoPago
from apps.usuarios.models import Rol, Usuario
from apps.compras.services import recibir_compra

class ComprasBaseTest(TestCase):
    """Pruebas de compras y asignación de almacén al lote (Fase 0)."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Almacenero")
        self.usuario = Usuario.objects.create_user(
            username="almacenero_test", password="password123", rol=self.rol
        )
        self.categoria = Categoria.objects.create(nombre="Materia Prima")
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            codigo="MP-01",
            nombre="Cacao en Grano",
            precio_compra_referencial=Decimal("8.00"),
            precio_venta=Decimal("12.00"),
        )
        self.almacen = Almacen.objects.create(nombre="Almacén Principal")
        self.proveedor = Proveedor.objects.create(razon_social="AgroCacao", ruc="20999888777")
        self.metodo_pago = MetodoPago.objects.create(nombre="Transferencia")
        self.compra = Compra.objects.create(
            proveedor=self.proveedor,
            usuario=self.usuario,
            numero_compra="COM-TEST-01",
            tipo_documento="FACTURA",
            fecha_compra=timezone.now(),
            total=Decimal("80.00"),
        )
        self.detalle = DetalleCompra.objects.create(
            compra=self.compra,
            producto=self.producto,
            cantidad=Decimal("10.000"),
            precio_unitario=Decimal("8.00"),
            subtotal=Decimal("80.00"),
        )

    def test_recibir_compra_asigna_almacen_a_lote(self):
        """Verifica que recibir_compra asigne el almacén correspondiente al Lote creado."""
        vencimiento = timezone.localdate() + timedelta(days=60)
        lotes_por_detalle = {
            self.detalle.pk: [{
                "codigo_lote": "LOTE-COMPRA-01",
                "fecha_vencimiento": vencimiento,
                "cantidad": Decimal("10.000"),
                "fecha_fabricacion": None,
            }]
        }

        recibir_compra(
            compra_id=self.compra.pk,
            almacen_id=self.almacen.pk,
            usuario=self.usuario,
            lotes_por_detalle=lotes_por_detalle,
        )

        lote = Lote.objects.get(codigo_lote="LOTE-COMPRA-01")
        self.assertEqual(lote.almacen, self.almacen)
        self.assertEqual(lote.producto, self.producto)
        self.assertEqual(lote.cantidad_disponible, Decimal("10.000"))

    def test_pago_compra_monto_check_constraint(self):
        """Verifica que PagoCompra impida montos negativos mediante CheckConstraint."""
        from django.db import transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PagoCompra.objects.create(
                    compra=self.compra,
                    metodo_pago=self.metodo_pago,
                    usuario=self.usuario,
                    monto=Decimal("-10.00"),
                    fecha_pago=timezone.now(),
                )
