from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.productos.models import Categoria, Producto
from apps.inventario.models import Almacen, Inventario, Lote, MovimientoInventario
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra
from apps.ventas.models import Venta, PagoVenta
from apps.configuracion.models import MetodoPago
from apps.caja.models import Caja, MovimientoCaja
from apps.usuarios.models import Rol, Usuario
from apps.ventas.services import registrar_venta, registrar_pago_venta, anular_venta

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
        self.assertEqual(venta.total, Decimal("11.80"))

        # Verificamos que el lote A se descontó (queda 1)
        self.lote_a.refresh_from_db()
        self.assertEqual(self.lote_a.cantidad_disponible, Decimal("1.000"))

        # Verificamos que el lote B quedó intacto (sigue 20)
        self.lote_b.refresh_from_db()
        self.assertEqual(self.lote_b.cantidad_disponible, Decimal("20.000"))

    def test_numero_igv_y_pagos_parciales(self):
        tarjeta = MetodoPago.objects.create(nombre="Tarjeta")
        venta = registrar_venta(
            usuario=self.usuario, almacen_id=self.almacen_a.pk,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                     "precio_unitario": Decimal("5.00")}],
            pagos=[{"metodo_pago_id": tarjeta.pk, "monto": Decimal("3.00")}],
        )
        self.assertEqual(venta.numero_venta, "VTA-000001")
        self.assertEqual(venta.igv, Decimal("0.90"))
        self.assertEqual(venta.total, Decimal("5.90"))
        self.assertEqual(venta.estado, "PARCIAL")
        registrar_pago_venta(
            venta_id=venta.pk, usuario=self.usuario, metodo_pago_id=tarjeta.pk,
            monto=Decimal("2.90"),
        )
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "PAGADA")
        self.assertEqual(venta.saldo_pendiente, Decimal("0.00"))

    def test_descuentos_por_linea_y_global_se_aplican_antes_del_igv(self):
        venta = registrar_venta(
            usuario=self.usuario, almacen_id=self.almacen_a.pk,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                     "precio_unitario": Decimal("5.00"), "descuento": Decimal("0.50")}],
            descuento=Decimal("0.50"),
        )
        self.assertEqual(venta.subtotal, Decimal("5.00"))
        self.assertEqual(venta.descuento, Decimal("1.00"))
        self.assertEqual(venta.igv, Decimal("0.72"))
        self.assertEqual(venta.total, Decimal("4.72"))

    def test_pago_en_efectivo_exige_caja_y_registra_ingreso(self):
        with self.assertRaisesMessage(ValidationError, "Abre una caja"):
            registrar_venta(
                usuario=self.usuario, almacen_id=self.almacen_a.pk,
                lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                         "precio_unitario": Decimal("5.00")}],
                pagos=[{"metodo_pago_id": self.metodo_pago.pk, "monto": Decimal("5.90")}],
            )
        caja = Caja.objects.create(
            usuario=self.usuario, fecha_apertura=timezone.now(), monto_inicial=Decimal("0.00"),
        )
        venta = registrar_venta(
            usuario=self.usuario, almacen_id=self.almacen_a.pk, caja=caja,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                     "precio_unitario": Decimal("5.00")}],
            pagos=[{"metodo_pago_id": self.metodo_pago.pk, "monto": Decimal("5.90")}],
        )
        movimiento = MovimientoCaja.objects.get(referencia_tipo="VENTA", referencia_id=venta.pk)
        self.assertEqual(movimiento.tipo, "INGRESO")
        self.assertEqual(movimiento.monto, Decimal("5.90"))

    def test_stock_reservado_es_opcional_y_se_guarda_por_detalle(self):
        existencia = Inventario.objects.get(producto=self.producto, almacen=self.almacen_a)
        existencia.stock_reservado = Decimal("1.000")
        existencia.save(update_fields=["stock_reservado"])
        with self.assertRaises(ValidationError):
            registrar_venta(
                usuario=self.usuario, almacen_id=self.almacen_a.pk,
                lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("3.000"),
                         "precio_unitario": Decimal("5.00")}],
            )
        venta = registrar_venta(
            usuario=self.usuario, almacen_id=self.almacen_a.pk,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("3.000"),
                     "precio_unitario": Decimal("5.00")}],
            usar_stock_reservado=True,
        )
        self.assertEqual(venta.detalles.get().cantidad_reservada, Decimal("1.000"))
        rol_admin = Rol.objects.create(nombre="Administrador")
        admin = Usuario.objects.create_user(username="admin_reserva", password="password123", rol=rol_admin)
        anular_venta(venta_id=venta.pk, usuario=admin, motivo="Restituir reserva")
        existencia.refresh_from_db()
        self.assertEqual(existencia.stock_actual, Decimal("3.000"))
        self.assertEqual(existencia.stock_reservado, Decimal("1.000"))

    def test_anular_venta_admin_restituye_lote_y_revierte_caja(self):
        rol_admin = Rol.objects.create(nombre="Administrador")
        admin = Usuario.objects.create_user(username="admin_ventas", password="password123", rol=rol_admin)
        caja = Caja.objects.create(usuario=admin, fecha_apertura=timezone.now(), monto_inicial=Decimal("0.00"))
        venta = registrar_venta(
            usuario=admin, almacen_id=self.almacen_a.pk, caja=caja,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"),
                     "precio_unitario": Decimal("5.00")}],
            pagos=[{"metodo_pago_id": self.metodo_pago.pk, "monto": Decimal("5.90")}],
        )
        anular_venta(venta_id=venta.pk, usuario=admin, motivo="Venta duplicada")
        venta.refresh_from_db()
        self.lote_a.refresh_from_db()
        existencia = Inventario.objects.get(producto=self.producto, almacen=self.almacen_a)
        self.assertEqual(venta.estado, "ANULADA")
        self.assertEqual(self.lote_a.cantidad_disponible, Decimal("3.000"))
        self.assertEqual(existencia.stock_actual, Decimal("3.000"))
        self.assertEqual(venta.pagos.get().estado, "ANULADO")
        tipos = list(MovimientoCaja.objects.filter(referencia_id=venta.pk).order_by("tipo").values_list("tipo", flat=True))
        self.assertEqual(tipos, ["EGRESO", "INGRESO"])

    def test_pos_cashless_crea_venta_y_muestra_historial_detalle_comprobante(self):
        tarjeta = MetodoPago.objects.create(nombre="Tarjeta")
        cliente = Client()
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.get(reverse("ventas:inicio")).status_code, 200)
        respuesta = cliente.post(reverse("ventas:inicio"), {
            "almacen": str(self.almacen_a.pk),
            "cliente": "",
            "descuento_global": "0.00",
            "carrito": '[{"producto_id":%d,"cantidad":"1.000","precio_unitario":"5.00","descuento":"0.00"}]' % self.producto.pk,
            "pagos": '[{"metodo_pago_id":%d,"monto":"5.90","referencia":"OP-1"}]' % tarjeta.pk,
            "modo_pago": "COBRAR",
        })
        venta = Venta.objects.get(estado="PAGADA")
        self.assertRedirects(respuesta, reverse("ventas:detalle", kwargs={"pk": venta.pk}))
        self.assertEqual(cliente.get(reverse("ventas:historial")).status_code, 200)
        self.assertEqual(cliente.get(reverse("ventas:detalle", kwargs={"pk": venta.pk})).status_code, 200)
        self.assertEqual(cliente.get(reverse("ventas:comprobante", kwargs={"pk": venta.pk})).status_code, 200)

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

    def test_fefo_descuenta_primero_el_lote_con_vencimiento_mas_cercano(self):
        lote_mas_proximo = Lote.objects.create(
            detalle_compra=self.detalle_compra, producto=self.producto,
            almacen=self.almacen_a, codigo_lote="LOTE-A-FEFO",
            fecha_vencimiento=timezone.localdate() + timedelta(days=10),
            cantidad_recibida=Decimal("2.000"), cantidad_disponible=Decimal("2.000"),
        )
        Inventario.objects.filter(producto=self.producto, almacen=self.almacen_a).update(
            stock_actual=Decimal("5.000"),
        )
        venta = registrar_venta(
            usuario=self.usuario, almacen_id=self.almacen_a.pk,
            lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("4.000"), "precio_unitario": Decimal("5.00")}],
        )
        lotes_venta = list(venta.detalles.order_by("pk").values_list("lote_id", "cantidad"))
        self.assertEqual(lotes_venta, [
            (lote_mas_proximo.pk, Decimal("2.000")),
            (self.lote_a.pk, Decimal("2.000")),
        ])

    def test_venta_no_usa_un_lote_vencido(self):
        self.lote_a.fecha_vencimiento = timezone.localdate() - timedelta(days=1)
        self.lote_a.save(update_fields=["fecha_vencimiento"])
        with self.assertRaises(ValidationError):
            registrar_venta(
                usuario=self.usuario, almacen_id=self.almacen_a.pk,
                lineas=[{"producto_id": self.producto.pk, "cantidad": Decimal("1.000"), "precio_unitario": Decimal("5.00")}],
            )
        self.assertFalse(Venta.objects.exists())

    def test_error_en_segunda_linea_revierte_toda_la_venta(self):
        segundo_producto = Producto.objects.create(
            categoria=self.categoria, codigo="TRUF-02", nombre="Trufa sin existencias",
            precio_compra_referencial=Decimal("2.00"), precio_venta=Decimal("5.00"),
        )
        stock_antes = Inventario.objects.get(producto=self.producto, almacen=self.almacen_a).stock_actual
        lote_antes = Lote.objects.get(pk=self.lote_a.pk).cantidad_disponible
        movimientos_antes = MovimientoCaja.objects.count()
        with self.assertRaises(ValidationError):
            registrar_venta(
                usuario=self.usuario, almacen_id=self.almacen_a.pk,
                lineas=[
                    {"producto_id": self.producto.pk, "cantidad": Decimal("1.000"), "precio_unitario": Decimal("5.00")},
                    {"producto_id": segundo_producto.pk, "cantidad": Decimal("1.000"), "precio_unitario": Decimal("5.00")},
                ],
            )
        self.assertFalse(Venta.objects.exists())
        self.assertEqual(Inventario.objects.get(producto=self.producto, almacen=self.almacen_a).stock_actual, stock_antes)
        self.assertEqual(Lote.objects.get(pk=self.lote_a.pk).cantidad_disponible, lote_antes)
        self.assertEqual(MovimientoCaja.objects.count(), movimientos_antes)
        self.assertFalse(MovimientoInventario.objects.filter(tipo_movimiento="SALIDA").exists())

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
