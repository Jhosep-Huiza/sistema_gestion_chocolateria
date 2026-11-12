from decimal import Decimal
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.caja.models import Caja, MovimientoCaja
from apps.usuarios.models import Rol, Usuario
from apps.caja.services import abrir_caja, cerrar_caja, registrar_movimiento_caja

class CajaBaseTest(TestCase):
    """Pruebas de Caja: restricción de una sola caja abierta por usuario y montos."""

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Cajero")
        self.usuario1 = Usuario.objects.create_user(
            username="cajero1", password="password123", rol=self.rol
        )
        self.usuario2 = Usuario.objects.create_user(
            username="cajero2", password="password123", rol=self.rol
        )

    def test_una_sola_caja_abierta_por_usuario(self):
        """No se debe permitir más de una caja con estado ABIERTA para el mismo usuario."""
        caja1 = Caja.objects.create(
            usuario=self.usuario1,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("100.00"),
            estado="ABIERTA",
        )
        self.assertIsNotNone(caja1.pk)

        # Otro usuario sí puede abrir una caja
        caja_otro = Caja.objects.create(
            usuario=self.usuario2,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("50.00"),
            estado="ABIERTA",
        )
        self.assertIsNotNone(caja_otro.pk)

        # Mismo usuario no puede abrir otra caja abierta (validación clean)
        caja_duplicada = Caja(
            usuario=self.usuario1,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("20.00"),
            estado="ABIERTA",
        )
        with self.assertRaises(ValidationError):
            caja_duplicada.clean()

    def test_caja_cerrada_permite_abrir_otra(self):
        """Si la caja anterior se cierra, el usuario puede abrir una nueva."""
        caja1 = Caja.objects.create(
            usuario=self.usuario1,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("100.00"),
            estado="CERRADA",
            fecha_cierre=timezone.now(),
        )
        caja2 = Caja(
            usuario=self.usuario1,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("100.00"),
            estado="ABIERTA",
        )
        caja2.clean()
        caja2.save()
        self.assertIsNotNone(caja2.pk)

    def test_caja_monto_inicial_check_constraint(self):
        """Monto inicial no puede ser negativo."""
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Caja.objects.create(
                    usuario=self.usuario1,
                    fecha_apertura=timezone.now(),
                    monto_inicial=Decimal("-10.00"),
                    estado="CERRADA",
                )

    def test_movimiento_caja_monto_check_constraint(self):
        """Monto en MovimientoCaja no puede ser negativo."""
        caja = Caja.objects.create(
            usuario=self.usuario1,
            fecha_apertura=timezone.now(),
            monto_inicial=Decimal("100.00"),
            estado="ABIERTA",
        )
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                MovimientoCaja.objects.create(
                    caja=caja,
                    usuario=self.usuario1,
                    tipo="INGRESO",
                    concepto="Ingreso prueba",
                    monto=Decimal("-20.00"),
                )

    def test_cierre_calcula_esperado_y_bloquea_movimientos_posteriores(self):
        caja = abrir_caja(usuario=self.usuario1, monto_inicial=Decimal("100.00"))
        registrar_movimiento_caja(
            caja_id=caja.pk, usuario=self.usuario1, tipo="INGRESO",
            concepto="Fondo recibido", monto=Decimal("25.00"),
        )
        registrar_movimiento_caja(
            caja_id=caja.pk, usuario=self.usuario1, tipo="EGRESO",
            concepto="Compra urgente", monto=Decimal("10.00"),
        )
        cerrada = cerrar_caja(caja_id=caja.pk, usuario=self.usuario1, monto_final=Decimal("113.00"))
        self.assertEqual(cerrada.monto_esperado, Decimal("115.00"))
        self.assertEqual(cerrada.diferencia, Decimal("-2.00"))
        with self.assertRaises(ValidationError):
            registrar_movimiento_caja(
                caja_id=caja.pk, usuario=self.usuario1, tipo="INGRESO",
                concepto="Tardío", monto=Decimal("1.00"),
            )

    def test_pantalla_caja_renderiza_para_cajero_autenticado(self):
        cliente = Client()
        cliente.force_login(self.usuario1)
        respuesta = cliente.get(reverse("caja:inicio"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Abrir una caja")
