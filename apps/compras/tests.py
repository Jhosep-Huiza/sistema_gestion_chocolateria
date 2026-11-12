from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db.utils import IntegrityError
from apps.productos.models import Categoria, Producto
from apps.inventario.models import Almacen, Lote
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra, PagoCompra
from apps.configuracion.models import MetodoPago
from apps.usuarios.models import Rol, Usuario
from apps.compras.services import recibir_compra, crear_compra, registrar_pago_compra, anular_compra
from apps.configuracion.models import Configuracion
from apps.inventario.models import Inventario, MovimientoInventario
from django.core.exceptions import ValidationError

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

    def test_crear_compra_calcula_descuento_igv_y_numero(self):
        Configuracion.objects.create(nombre_negocio="ChocoGest", porcentaje_igv=Decimal("18.00"), moneda="PEN")
        compra = crear_compra(
            proveedor_id=self.proveedor.pk,
            usuario=self.usuario,
            tipo_documento="FACTURA",
            numero_documento="F001-20",
            lineas=[{
                "producto_id": self.producto.pk,
                "cantidad": Decimal("2.000"),
                "precio_unitario": Decimal("10.00"),
                "descuento": Decimal("1.00"),
            }],
        )
        self.assertRegex(compra.numero_compra, r"^COMP-\d{6}$")
        self.assertEqual(compra.subtotal, Decimal("20.00"))
        self.assertEqual(compra.descuento, Decimal("1.00"))
        self.assertEqual(compra.igv, Decimal("3.42"))
        self.assertEqual(compra.total, Decimal("22.42"))

    def test_pago_compra_no_supera_saldo_pendiente(self):
        pago = registrar_pago_compra(
            compra_id=self.compra.pk, usuario=self.usuario,
            metodo_pago_id=self.metodo_pago.pk, monto=Decimal("30.00"),
        )
        self.assertEqual(pago.monto, Decimal("30.00"))
        self.assertEqual(self.compra.saldo_pendiente, Decimal("50.00"))
        with self.assertRaises(ValidationError):
            registrar_pago_compra(
                compra_id=self.compra.pk, usuario=self.usuario,
                metodo_pago_id=self.metodo_pago.pk, monto=Decimal("50.01"),
            )

    def test_anular_compra_recibida_revierte_stock_y_registra_movimientos(self):
        vencimiento = timezone.localdate() + timedelta(days=60)
        recibir_compra(
            compra_id=self.compra.pk, almacen_id=self.almacen.pk, usuario=self.usuario,
            lotes_por_detalle={self.detalle.pk: [
                {"codigo_lote": "LOTE-ANULAR-A", "fecha_vencimiento": vencimiento,
                 "cantidad": Decimal("4.000")},
                {"codigo_lote": "LOTE-ANULAR-B", "fecha_vencimiento": vencimiento,
                 "cantidad": Decimal("6.000")},
            ]},
        )
        anular_compra(compra_id=self.compra.pk, usuario=self.usuario)
        self.compra.refresh_from_db()
        existencia = Inventario.objects.get(producto=self.producto, almacen=self.almacen)
        self.assertEqual(self.compra.estado, "ANULADA")
        self.assertEqual(existencia.stock_actual, Decimal("0.000"))
        self.assertEqual(
            MovimientoInventario.objects.filter(referencia_id=self.compra.pk, tipo_movimiento="AJUSTE_NEGATIVO").count(),
            2,
        )

    def test_anular_compra_recibida_rechaza_lote_consumido(self):
        vencimiento = timezone.localdate() + timedelta(days=60)
        recibir_compra(
            compra_id=self.compra.pk, almacen_id=self.almacen.pk, usuario=self.usuario,
            lotes_por_detalle={self.detalle.pk: [{
                "codigo_lote": "LOTE-CONSUMIDO", "fecha_vencimiento": vencimiento,
                "cantidad": Decimal("10.000"),
            }]},
        )
        lote = Lote.objects.get(codigo_lote="LOTE-CONSUMIDO")
        lote.cantidad_disponible = Decimal("9.000")
        lote.save(update_fields=["cantidad_disponible"])
        with self.assertRaisesMessage(ValidationError, "tuvo consumo o movimientos posteriores"):
            anular_compra(compra_id=self.compra.pk, usuario=self.usuario)

    def test_pantalla_crea_compra_con_formset_y_muestra_detalle(self):
        cliente = Client()
        cliente.force_login(self.usuario)
        respuesta_formulario = cliente.get(reverse("compras:crear"))
        self.assertEqual(respuesta_formulario.status_code, 200)
        self.assertContains(respuesta_formulario, "lineas-TOTAL_FORMS")
        respuesta = cliente.post(reverse("compras:crear"), {
            "proveedor": self.proveedor.pk,
            "tipo_documento": "FACTURA",
            "numero_documento": "F001-TEST",
            "observaciones": "Pedido de prueba",
            "lineas-TOTAL_FORMS": "1",
            "lineas-INITIAL_FORMS": "0",
            "lineas-MIN_NUM_FORMS": "1",
            "lineas-MAX_NUM_FORMS": "1000",
            "lineas-0-producto": self.producto.pk,
            "lineas-0-cantidad": "2.000",
            "lineas-0-precio_unitario": "8.00",
            "lineas-0-descuento": "0.00",
        })
        compra_creada = Compra.objects.get(numero_documento="F001-TEST")
        self.assertRedirects(respuesta, reverse("compras:detalle", kwargs={"pk": compra_creada.pk}))
        self.assertEqual(cliente.get(reverse("compras:detalle", kwargs={"pk": compra_creada.pk})).status_code, 200)

    def test_pantalla_recepcion_registra_varios_lotes_y_valida_la_suma(self):
        cliente = Client()
        cliente.force_login(self.usuario)
        url = reverse("compras:recepcion", kwargs={"pk": self.compra.pk})
        self.assertEqual(cliente.get(url).status_code, 200)
        datos = {
            "almacen": self.almacen.pk,
            "lotes-TOTAL_FORMS": "2", "lotes-INITIAL_FORMS": "0",
            "lotes-MIN_NUM_FORMS": "1", "lotes-MAX_NUM_FORMS": "1000",
        }
        for indice, cantidad, codigo in [(0, "4.000", "LOTE-VISTA-A"), (1, "6.000", "LOTE-VISTA-B")]:
            datos.update({
                f"lotes-{indice}-detalle": self.detalle.pk,
                f"lotes-{indice}-codigo_lote": codigo,
                f"lotes-{indice}-fecha_fabricacion": "",
                f"lotes-{indice}-fecha_vencimiento": (timezone.localdate() + timedelta(days=60)).isoformat(),
                f"lotes-{indice}-cantidad": cantidad,
            })
        respuesta = cliente.post(url, datos)
        self.assertRedirects(respuesta, reverse("compras:detalle", kwargs={"pk": self.compra.pk}))
        self.compra.refresh_from_db()
        self.assertEqual(self.compra.estado, "RECIBIDA")
        self.assertEqual(Inventario.objects.filter(producto=self.producto, almacen=self.almacen).get().stock_actual, Decimal("10.000"))
