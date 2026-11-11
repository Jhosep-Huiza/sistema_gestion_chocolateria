from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.core.exceptions import ImproperlyConfigured
from apps.configuracion.models import Configuracion
from apps.configuracion.context_processors import configuracion_negocio

class ConfiguracionContextProcessorTest(TestCase):
    """Pruebas del context processor de configuración (Fase 0)."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_context_processor_valores_por_defecto(self):
        """Si no hay registro en Configuracion, devuelve valores seguros por defecto."""
        request = self.factory.get("/")
        ctx = configuracion_negocio(request)
        self.assertIn("configuracion", ctx)
        self.assertEqual(ctx["nombre_negocio"], "ChocoGest")
        self.assertEqual(ctx["moneda_negocio"], "PEN")
        self.assertEqual(ctx["igv_negocio"], 18)

    def test_context_processor_con_configuracion_guardada(self):
        """Expone los datos reales de la BD en el contexto de plantilla."""
        Configuracion.objects.create(
            nombre_negocio="Chocolatería Artesanal Cacao Dorado",
            ruc="20456789012",
            porcentaje_igv=Decimal("18.00"),
            moneda="PEN",
        )
        request = self.factory.get("/")
        ctx = configuracion_negocio(request)
        self.assertEqual(ctx["nombre_negocio"], "Chocolatería Artesanal Cacao Dorado")
        self.assertEqual(ctx["moneda_negocio"], "PEN")
        self.assertEqual(ctx["igv_negocio"], Decimal("18.00"))


class SeguridadSettingsTest(TestCase):
    """Prueba que SECRET_KEY lance ImproperlyConfigured cuando DEBUG=False y se use la clave por defecto."""

    def test_secret_key_sin_valor_seguro_con_debug_false_lanza_error(self):
        import importlib
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"DEBUG": "False", "SECRET_KEY": "development-only-change-me"}):
            with self.assertRaises(ImproperlyConfigured):
                import config.settings
                importlib.reload(config.settings)

        # Restaurar estado válido para no afectar otros tests
        with patch.dict(os.environ, {"DEBUG": "True", "SECRET_KEY": "admin1234567890"}):
            import config.settings
            importlib.reload(config.settings)
