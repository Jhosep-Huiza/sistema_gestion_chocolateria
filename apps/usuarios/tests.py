from django.test import TestCase, Client
from django.urls import reverse
from apps.usuarios.models import Rol, Usuario
from apps.usuarios.models import Auditoria
from django.core.management import call_command
from apps.inventario.models import Almacen
from apps.productos.models import Producto
from apps.configuracion.models import Configuracion

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

    def test_login_y_logout_se_registran_con_ip(self):
        self.client.post(reverse("login"), {
            "username": "testuser", "password": "secretpassword123",
        }, REMOTE_ADDR="192.0.2.15")
        evento = Auditoria.objects.get(accion="LOGIN")
        self.assertEqual(evento.usuario, self.usuario)
        self.assertEqual(evento.direccion_ip, "192.0.2.15")
        self.client.post(reverse("logout"), REMOTE_ADDR="192.0.2.16")
        evento_salida = Auditoria.objects.get(accion="LOGOUT")
        self.assertEqual(evento_salida.direccion_ip, "192.0.2.16")

    def test_permisos_de_modulos_segun_rol(self):
        vendedor = Usuario.objects.create_user(
            username="vendedor", password="secretpassword123",
            rol=Rol.objects.create(nombre="Vendedor"),
        )
        self.client.force_login(vendedor)
        for nombre_url in ["ventas:inicio", "clientes:listado", "productos:listado", "devoluciones:inicio",
                           "inventario:stock", "inventario:lotes", "inventario:movimientos"]:
            self.assertEqual(self.client.get(reverse(nombre_url)).status_code, 200)
        for nombre_url in ["caja:inicio", "compras:listado", "inventario:ajustar", "inventario:transferir", "finanzas:inicio"]:
            self.assertRedirects(self.client.get(reverse(nombre_url)), reverse("dashboard"))

    def test_matriz_de_acceso_de_los_cuatro_roles(self):
        roles = {
            "Administrador": self.rol,
            "Vendedor": Rol.objects.create(nombre="Vendedor"),
            "Cajero": Rol.objects.create(nombre="Cajero"),
            "Almacenero": Rol.objects.create(nombre="Almacenero"),
        }
        usuarios = {
            nombre: Usuario.objects.create_user(
                username=f"matriz_{nombre.lower()}", password="secretpassword123", rol=rol,
            )
            for nombre, rol in roles.items()
        }
        accesos = {
            "clientes:listado": {"Administrador", "Vendedor"},
            "productos:listado": {"Administrador", "Vendedor", "Almacenero"},
            "proveedores:listado": {"Administrador", "Almacenero"},
            "compras:listado": {"Administrador", "Almacenero"},
            "inventario:stock": {"Administrador", "Vendedor", "Almacenero"},
            "inventario:ajustar": {"Administrador", "Almacenero"},
            "ventas:inicio": {"Administrador", "Vendedor", "Cajero"},
            "ventas:historial": {"Administrador", "Vendedor", "Cajero"},
            "devoluciones:listado": {"Administrador", "Vendedor"},
            "caja:inicio": {"Administrador", "Cajero"},
            "finanzas:inicio": {"Administrador"},
            "reportes:inicio": {"Administrador"},
            "configuracion:inicio": {"Administrador"},
            "usuarios:listado": {"Administrador"},
        }
        for rol, usuario in usuarios.items():
            self.client.force_login(usuario)
            for nombre_url, roles_permitidos in accesos.items():
                with self.subTest(rol=rol, url=nombre_url):
                    respuesta = self.client.get(reverse(nombre_url))
                    if rol in roles_permitidos:
                        self.assertEqual(respuesta.status_code, 200)
                    else:
                        self.assertEqual(respuesta.status_code, 302)
                        self.assertEqual(respuesta.url, reverse("dashboard"))

    def test_comando_de_datos_iniciales_es_idempotente(self):
        call_command("cargar_datos_iniciales", verbosity=0)
        conteo_productos = Producto.objects.count()
        call_command("cargar_datos_iniciales", verbosity=0)
        self.assertEqual(Producto.objects.count(), conteo_productos)
        self.assertTrue(Almacen.objects.filter(nombre="Almacén principal").exists())
        self.assertEqual(Configuracion.objects.count(), 1)
        self.assertEqual(Configuracion.objects.first().moneda, "PEN")
