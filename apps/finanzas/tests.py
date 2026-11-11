from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.db.utils import IntegrityError
from apps.finanzas.models import Gasto
from apps.usuarios.models import Rol, Usuario

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
