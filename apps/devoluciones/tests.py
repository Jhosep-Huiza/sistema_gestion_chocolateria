from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone
from django.urls import reverse

from apps.caja.models import Caja, MovimientoCaja
from apps.compras.models import Compra, DetalleCompra
from apps.configuracion.models import MetodoPago
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.productos.models import Categoria, Producto
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Rol, Usuario
from apps.ventas.services import registrar_venta
from .models import Devolucion
from .services import aprobar_devolucion, rechazar_devolucion, solicitar_devolucion


class FlujoDevolucionesTest(TestCase):
    def setUp(self):
        self.rol_vendedor = Rol.objects.create(nombre="Vendedor")
        self.rol_admin = Rol.objects.create(nombre="Administrador")
        self.vendedor = Usuario.objects.create_user(username="vendedor_dev", password="pass", rol=self.rol_vendedor)
        self.admin = Usuario.objects.create_user(username="admin_dev", password="pass", rol=self.rol_admin)
        categoria = Categoria.objects.create(nombre="Bombones")
        self.producto = Producto.objects.create(
            categoria=categoria, codigo="BOM-01", nombre="Bombón",
            precio_compra_referencial=Decimal("2.00"), precio_venta=Decimal("10.00"),
        )
        self.almacen = Almacen.objects.create(nombre="Principal")
        proveedor = Proveedor.objects.create(razon_social="Cacao SAC", ruc="20111222333")
        compra = Compra.objects.create(
            proveedor=proveedor, usuario=self.vendedor, numero_compra="COMP-DEV-1",
            tipo_documento="BOLETA", fecha_compra=timezone.now(),
        )
        detalle_compra = DetalleCompra.objects.create(
            compra=compra, producto=self.producto, cantidad=Decimal("20.000"),
            precio_unitario=Decimal("2.00"), subtotal=Decimal("40.00"),
        )
        self.lote = Lote.objects.create(
            detalle_compra=detalle_compra, producto=self.producto, almacen=self.almacen,
            codigo_lote="BOM-LOTE", fecha_vencimiento=timezone.localdate() + timedelta(days=45),
            cantidad_recibida=Decimal("10.000"), cantidad_disponible=Decimal("10.000"),
        )
        Inventario.objects.create(producto=self.producto, almacen=self.almacen, stock_actual=Decimal("10.000"))
        self.efectivo = MetodoPago.objects.create(nombre="Efectivo")
        self.caja = Caja.objects.create(
            usuario=self.vendedor, fecha_apertura=timezone.now(), monto_inicial=Decimal("50.00"),
            estado="ABIERTA",
        )
        self.venta = registrar_venta(
            usuario=self.vendedor, almacen_id=self.almacen.pk,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("2.000"), "precio_unitario": Decimal("10.00")}],
            pagos=[{"metodo_pago_id": self.efectivo.pk, "monto": Decimal("23.60")}], caja=self.caja,
        )
        self.detalle_venta = self.venta.detalles.get()

    def _solicitar(self, estado, cantidad="1.000", tipo="REEMBOLSO", efectivo=False):
        return solicitar_devolucion(
            venta_id=self.venta.pk, usuario=self.vendedor, motivo="Producto no deseado",
            tipo_reembolso=tipo, reembolso_efectivo=efectivo,
            detalles=[{"detalle_venta_id": self.detalle_venta.pk, "cantidad": cantidad, "estado_producto": estado}],
        )

    def test_solicitudes_pendientes_reservan_cantidad_y_no_superan_vendido(self):
        self._solicitar("REINGRESAR", "1.000")
        with self.assertRaises(ValidationError):
            self._solicitar("REINGRESAR", "1.001")

    def test_aprobacion_reingresa_a_mismo_lote_y_registra_kardex(self):
        devolucion = self._solicitar("REINGRESAR")
        aprobar_devolucion(devolucion_id=devolucion.pk, usuario=self.admin)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_disponible, Decimal("9.000"))
        self.assertTrue(MovimientoInventario.objects.filter(
            referencia_tipo="DEVOLUCION", referencia_id=devolucion.pk,
            lote=self.lote, tipo_movimiento="DEVOLUCION", cantidad=Decimal("1.000"),
        ).exists())

    def test_cuarentena_crea_lote_separado_y_danado_no_repone_stock(self):
        cuarentena = self._solicitar("CUARENTENA")
        aprobar_devolucion(devolucion_id=cuarentena.pk, usuario=self.admin)
        lote_cuarentena = Lote.objects.get(codigo_lote__contains=f"-DEV-{cuarentena.pk}-")
        self.assertEqual(lote_cuarentena.estado, "CUARENTENA")
        self.assertEqual(lote_cuarentena.cantidad_disponible, Decimal("1.000"))
        antes = Inventario.objects.get(producto=self.producto, almacen=self.almacen).stock_actual
        danado = self._solicitar("DANADO")
        aprobar_devolucion(devolucion_id=danado.pk, usuario=self.admin)
        despues = Inventario.objects.get(producto=self.producto, almacen=self.almacen).stock_actual
        self.assertEqual(despues, antes)
        self.assertFalse(MovimientoInventario.objects.filter(referencia_tipo="DEVOLUCION", referencia_id=danado.pk).exists())

    def test_reembolso_efectivo_genera_egreso_y_vendedor_no_puede_aprobar(self):
        devolucion = self._solicitar("DANADO", efectivo=True)
        with self.assertRaises(ValidationError):
            aprobar_devolucion(devolucion_id=devolucion.pk, usuario=self.vendedor)
        aprobar_devolucion(devolucion_id=devolucion.pk, usuario=self.admin, efectivo=True)
        self.assertTrue(MovimientoCaja.objects.filter(
            caja=self.caja, tipo="EGRESO", referencia_tipo="DEVOLUCION", referencia_id=devolucion.pk,
        ).exists())

    def test_rechazo_libera_la_cantidad_solicitada(self):
        devolucion = self._solicitar("REINGRESAR", "2.000")
        rechazar_devolucion(devolucion_id=devolucion.pk, usuario=self.admin, motivo="Fuera de plazo")
        nueva = self._solicitar("REINGRESAR", "2.000")
        self.assertEqual(nueva.estado, "PENDIENTE")

    def test_vendedor_puede_solicitar_y_cargar_renglones_de_venta(self):
        cliente = Client()
        cliente.force_login(self.vendedor)
        respuesta = cliente.get(reverse("devoluciones:crear"), {"venta": self.venta.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.producto.nombre)
        respuesta = cliente.post(reverse("devoluciones:crear"), {
            "venta": self.venta.pk, "motivo": "Empaque dañado", "tipo_reembolso": "REEMBOLSO",
            "lineas-TOTAL_FORMS": "1", "lineas-INITIAL_FORMS": "1",
            "lineas-MIN_NUM_FORMS": "0", "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-detalle_venta_id": self.detalle_venta.pk,
            "lineas-0-cantidad": "1.000", "lineas-0-estado_producto": "DANADO",
        })
        self.assertRedirects(respuesta, reverse("devoluciones:listado"))
        self.assertEqual(Devolucion.objects.count(), 1)

    def test_vendedor_no_puede_abrir_aprobacion_de_admin(self):
        devolucion = self._solicitar("DANADO")
        cliente = Client()
        cliente.force_login(self.vendedor)
        respuesta = cliente.post(reverse("devoluciones:aprobar", args=[devolucion.pk]))
        self.assertEqual(respuesta.status_code, 302)
        devolucion.refresh_from_db()
        self.assertEqual(devolucion.estado, "PENDIENTE")
