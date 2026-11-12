from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.caja.models import Caja, MovimientoCaja
from apps.compras.models import Compra, PagoCompra
from apps.configuracion.models import MetodoPago
from apps.finanzas.models import Gasto
from apps.finanzas.services import anular_gasto, registrar_gasto, resumen_financiero
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Rol, Usuario
from apps.ventas.models import Venta, PagoVenta

class FinanzasBaseTest(TestCase):
    """Pruebas de modelos de finanzas (Fase 0)."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Administrador")
        self.usuario = Usuario.objects.create_user(
            username="admin_finanzas", password="password123", rol=self.rol
        )

    def test_gasto_monto_check_constraint(self):
        """Monto de gasto no puede ser negativo."""
        from django.db import transaction
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Gasto.objects.create(
                    usuario=self.usuario,
                    categoria="Servicios",
                    descripcion="Pago luz",
                    monto=Decimal("-50.00"),
                    fecha_gasto=timezone.now(),
                )

    def test_gasto_efectivo_registra_egreso_y_anulacion_reversa(self):
        caja = Caja.objects.create(
            usuario=self.usuario, fecha_apertura=timezone.now(), monto_inicial=Decimal("100.00"),
        )
        gasto = registrar_gasto(
            usuario=self.usuario, categoria="Insumos", descripcion="Bolsas",
            monto=Decimal("12.35"), fecha_gasto=timezone.now(), es_efectivo=True,
            caja_id=caja.pk,
        )
        egreso = MovimientoCaja.objects.get(referencia_tipo="GASTO", referencia_id=gasto.pk)
        self.assertEqual(egreso.tipo, "EGRESO")
        anular_gasto(gasto_id=gasto.pk, usuario=self.usuario, motivo="Duplicado")
        self.assertEqual(MovimientoCaja.objects.filter(
            referencia_tipo="ANULACION_GASTO", referencia_id=gasto.pk, tipo="INGRESO",
        ).count(), 1)
        gasto.refresh_from_db()
        self.assertEqual(gasto.estado, "ANULADO")

    def test_resumen_financiero_suma_cobranzas_pagos_gastos_y_saldos(self):
        metodo = MetodoPago.objects.create(nombre="Transferencia")
        venta = Venta.objects.create(
            usuario=self.usuario, numero_venta="VTA-FIN-1", fecha_venta=timezone.now(),
            subtotal=Decimal("100.00"), igv=Decimal("18.00"), total=Decimal("118.00"),
        )
        PagoVenta.objects.create(
            venta=venta, metodo_pago=metodo, usuario=self.usuario, monto=Decimal("40.00"),
            fecha_pago=timezone.now(),
        )
        proveedor = Proveedor.objects.create(razon_social="Proveedor resumen", ruc="20111222333")
        compra = Compra.objects.create(
            proveedor=proveedor, usuario=self.usuario, numero_compra="COMP-FIN-1",
            tipo_documento="FACTURA", fecha_compra=timezone.now(), total=Decimal("50.00"),
        )
        PagoCompra.objects.create(
            compra=compra, metodo_pago=metodo, usuario=self.usuario, monto=Decimal("15.00"),
            fecha_pago=timezone.now(),
        )
        Gasto.objects.create(
            usuario=self.usuario, categoria="Servicios", monto=Decimal("5.00"), fecha_gasto=timezone.now(),
        )
        resumen = resumen_financiero()
        self.assertEqual(resumen["ingresos_ventas"], Decimal("40.00"))
        self.assertEqual(resumen["egresos_compras"], Decimal("15.00"))
        self.assertEqual(resumen["egresos_gastos"], Decimal("5.00"))
        self.assertEqual(resumen["utilidad"], Decimal("20.00"))
        self.assertEqual(resumen["por_cobrar"], Decimal("78.00"))
        self.assertEqual(resumen["por_pagar"], Decimal("35.00"))

    def test_vistas_financieras_renderizan_para_administrador(self):
        cliente = Client()
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.get(reverse("finanzas:inicio")).status_code, 200)
        self.assertEqual(cliente.get(reverse("finanzas:gastos")).status_code, 200)
        self.assertEqual(cliente.get(reverse("finanzas:gasto_crear")).status_code, 200)
