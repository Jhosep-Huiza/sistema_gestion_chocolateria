from django.test import TestCase, Client
from django.urls import reverse
from apps.usuarios.models import Rol, Usuario

class UsuarioLoginSeguridadTest(TestCase):
    """Pruebas de seguridad de login (Fase 0): validación de next y redirecciones seguras."""

    def setUp(self):
        self.client = Client()
        self.rol = Rol.objects.create(nombre="Administrador")
        self.usuario = Usuario.objects.create_user(
            username="testuser", password="secretpassword123", rol=self.rol
        )

    def test_login_con_next_valido(self):
        """Redirige al next si es interno y seguro."""
        response = self.client.post(
            reverse("login") + "?next=/productos/",
            {"username": "testuser", "password": "secretpassword123"},
        )
        self.assertRedirects(response, "/productos/", fetch_redirect_response=False)

    def test_login_con_next_malicioso_redirige_a_dashboard(self):
        """Rechaza URLs externas o maliciosas en next redirigiendo a dashboard."""
        urls_maliciosas = [
            "https://evil.com",
            "http://malicious-site.org/phish",
            "//evil.com/fake-login",
            "javascript:alert(1)",
        ]
        for url in urls_maliciosas:
            response = self.client.post(
                reverse("login") + f"?next={url}",
                {"username": "testuser", "password": "secretpassword123"},
            )
            self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
