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
from apps.inventario.services import ajustar_inventario, transferir_stock, cambiar_estado_lote
from apps.inventario.services import marcar_lotes_vencidos
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

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

    def test_ajustar_inventario_actualiza_lote_stock_y_kardex(self):
        lote = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto, almacen=self.almacen1,
            codigo_lote="AJUSTE-01", fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("10.000"), cantidad_disponible=Decimal("10.000"),
        )
        inventario, _ = Inventario.objects.get_or_create(
            producto=self.producto, almacen=self.almacen1,
            defaults={"stock_actual": Decimal("10.000")},
        )
        movimiento = ajustar_inventario(
            lote_id=lote.pk, cantidad=Decimal("2.000"), tipo="NEGATIVO",
            motivo="Conteo físico", usuario=self.usuario,
        )
        inventario.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(inventario.stock_actual, Decimal("8.000"))
        self.assertEqual(lote.cantidad_disponible, Decimal("8.000"))
        self.assertEqual(movimiento.tipo_movimiento, "AJUSTE_NEGATIVO")
        self.assertEqual(movimiento.motivo, "Conteo físico")

    def test_transferir_stock_crea_lote_destino_y_dos_movimientos(self):
        lote = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto, almacen=self.almacen1,
            codigo_lote="TRANS-01", fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("10.000"), cantidad_disponible=Decimal("10.000"),
        )
        Inventario.objects.create(producto=self.producto, almacen=self.almacen1, stock_actual=Decimal("10.000"))
        salida, entrada = transferir_stock(
            lote_id=lote.pk, almacen_destino_id=self.almacen2.pk,
            cantidad=Decimal("4.000"), motivo="Rebalanceo", usuario=self.usuario,
        )
        lote.refresh_from_db()
        destino = Lote.objects.get(producto=self.producto, almacen=self.almacen2, codigo_lote="TRANS-01")
        self.assertEqual(lote.cantidad_disponible, Decimal("6.000"))
        self.assertEqual(destino.cantidad_disponible, Decimal("4.000"))
        self.assertEqual(salida.tipo_movimiento, "SALIDA")
        self.assertEqual(entrada.tipo_movimiento, "ENTRADA")
        self.assertEqual(salida.referencia_id, entrada.pk)
        self.assertEqual(entrada.referencia_id, salida.pk)

    def test_cambiar_estado_lote_no_modifica_stock(self):
        lote = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto, almacen=self.almacen1,
            codigo_lote="ESTADO-01", fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("5.000"), cantidad_disponible=Decimal("5.000"),
        )
        inventario = Inventario.objects.create(producto=self.producto, almacen=self.almacen1, stock_actual=Decimal("5.000"))
        cambiar_estado_lote(lote_id=lote.pk, estado="CUARENTENA", usuario=self.usuario)
        inventario.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(lote.estado, "CUARENTENA")
        self.assertEqual(inventario.stock_actual, Decimal("5.000"))
        with self.assertRaises(ValidationError):
            transferir_stock(lote_id=lote.pk, almacen_destino_id=self.almacen2.pk,
                             cantidad=Decimal("1.000"), motivo="Prueba", usuario=self.usuario)

    def test_marcar_lotes_vencidos_resta_stock_y_es_idempotente(self):
        lote = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto, almacen=self.almacen1,
            codigo_lote="VENCIDO-01", fecha_vencimiento=timezone.localdate() - timedelta(days=1),
            cantidad_recibida=Decimal("5.000"), cantidad_disponible=Decimal("5.000"),
        )
        inventario = Inventario.objects.create(producto=self.producto, almacen=self.almacen1, stock_actual=Decimal("5.000"))
        primero = marcar_lotes_vencidos()
        segundo = marcar_lotes_vencidos()
        lote.refresh_from_db()
        inventario.refresh_from_db()
        self.assertEqual(primero, {"marcados": 1, "movimientos": 1})
        self.assertEqual(segundo, {"marcados": 0, "movimientos": 0})
        self.assertEqual(lote.estado, "VENCIDO")
        self.assertEqual(lote.cantidad_disponible, Decimal("0.000"))
        self.assertEqual(inventario.stock_actual, Decimal("0.000"))

    def test_listados_de_inventario_y_restriccion_de_ajustes(self):
        lote = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto, almacen=self.almacen1,
            codigo_lote="LECTURA-VENDEDOR", fecha_vencimiento=timezone.localdate() + timedelta(days=30),
            cantidad_recibida=Decimal("1.000"), cantidad_disponible=Decimal("1.000"),
        )
        cliente = Client()
        vendedor = Usuario.objects.create_user(
            username="vendedor_stock", password="password123",
            rol=Rol.objects.create(nombre="Vendedor"),
        )
        cliente.force_login(vendedor)
        for nombre_url in ["inventario:stock", "inventario:lotes", "inventario:movimientos"]:
            self.assertEqual(cliente.get(reverse(nombre_url)).status_code, 200)
        self.assertEqual(cliente.get(reverse("inventario:lote_detalle", kwargs={"pk": lote.pk})).status_code, 200)
        respuesta = cliente.post(reverse("inventario:ajustar"), {})
        self.assertRedirects(respuesta, reverse("dashboard"))
