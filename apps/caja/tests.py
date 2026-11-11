from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.db import transaction
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from apps.caja.models import Caja, MovimientoCaja
from apps.usuarios.models import Rol, Usuario

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
