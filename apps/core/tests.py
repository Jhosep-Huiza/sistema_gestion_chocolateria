from decimal import Decimal
from django.contrib import admin
from django.test import RequestFactory
from django.test import TestCase, Client
from django.urls import reverse
from django.db import models
from django.db.models import ProtectedError
from django.utils import timezone
from apps.usuarios.models import Rol, Usuario
from apps.productos.models import Categoria, Marca, Producto
from apps.inventario.models import Almacen, Inventario, Lote
from apps.proveedores.models import Proveedor
from apps.compras.models import Compra, DetalleCompra, PagoCompra
from apps.configuracion.models import MetodoPago, Configuracion
from apps.ventas.models import Venta, DetalleVenta, PagoVenta
from apps.inventario.models import MovimientoInventario
from apps.caja.models import Caja, MovimientoCaja
from apps.devoluciones.models import Devolucion, DetalleDevolucion
from apps.finanzas.models import Gasto

class CoreInfraestructuraTest(TestCase):
    """Pruebas de la infraestructura reutilizable de vistas, mixins y plantillas (Fase 1)."""

    def setUp(self):
        self.client = Client()

        # Roles
        self.rol_admin = Rol.objects.create(nombre="Administrador")
        self.rol_vendedor = Rol.objects.create(nombre="Vendedor")
        self.rol_cajero = Rol.objects.create(nombre="Cajero")
        self.rol_almacenero = Rol.objects.create(nombre="Almacenero")

        # Usuarios
        self.admin = Usuario.objects.create_user(
            username="admin", password="password123", rol=self.rol_admin
        )
        self.vendedor = Usuario.objects.create_user(
            username="vendedor", password="password123", rol=self.rol_vendedor
        )
        self.cajero = Usuario.objects.create_user(
            username="cajero", password="password123", rol=self.rol_cajero
        )
        self.almacenero = Usuario.objects.create_user(
            username="almacenero", password="password123", rol=self.rol_almacenero
        )

    def test_listado_paginacion_y_busqueda(self):
        """Verifica que BaseListView pagine a 20 registros y responda a búsquedas con q."""
        self.client.force_login(self.admin)
        categoria = Categoria.objects.create(nombre="Tabletas")

        # Creamos 25 productos
        for i in range(1, 26):
            Producto.objects.create(
                categoria=categoria,
                codigo=f"PROD-{i:03d}",
                nombre=f"Chocolate Barra {i}",
                precio_compra_referencial=Decimal("3.00"),
                precio_venta=Decimal("8.00"),
            )

        # Página 1 (debe contener 20 productos)
        response = self.client.get(reverse("productos:listado"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["registros"]), 20)
        self.assertContains(response, "Mostrando registros 1 - 20 de 25")

        # Página 2 (debe contener 5 productos)
        response_page2 = self.client.get(reverse("productos:listado") + "?page=2")
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(response_page2.context["registros"]), 5)

        # Búsqueda por q
        response_search = self.client.get(reverse("productos:listado") + "?q=PROD-015")
        self.assertEqual(response_search.status_code, 200)
        self.assertEqual(len(response_search.context["registros"]), 1)
        self.assertContains(response_search, "Chocolate Barra 15")

    def test_base_delete_view_captura_protected_error_y_desactiva(self):
        """
        Al eliminar un registro con dependencias PROTECT, BaseDeleteView debe capturar
        ProtectedError, cambiar estado=False y mostrar una advertencia amable.
        """
        self.client.force_login(self.admin)
        categoria = Categoria.objects.create(nombre="Trufas Finas")
        producto = Producto.objects.create(
            categoria=categoria,
            codigo="TRUF-DEL-01",
            nombre="Trufa de Maracuyá",
            precio_compra_referencial=Decimal("2.00"),
            precio_venta=Decimal("6.00"),
            estado=True,
        )
        almacen = Almacen.objects.create(nombre="Almacén de Muestra")
        proveedor = Proveedor.objects.create(razon_social="Proveedor Frutas", ruc="20444555666")
        compra = Compra.objects.create(
            proveedor=proveedor,
            usuario=self.admin,
            numero_compra="COM-DEL-01",
            tipo_documento="FACTURA",
            fecha_compra=timezone.now(),
        )
        detalle_compra = DetalleCompra.objects.create(
            compra=compra,
            producto=producto,
            cantidad=Decimal("5.000"),
            precio_unitario=Decimal("2.00"),
            subtotal=Decimal("10.00"),
        )
        # Lote tiene on_delete=PROTECT hacia producto
        Lote.objects.create(
            detalle_compra=detalle_compra,
            producto=producto,
            almacen=almacen,
            codigo_lote="LOT-PROTECT",
            fecha_vencimiento="2026-12-31",
            cantidad_recibida=Decimal("5.000"),
            cantidad_disponible=Decimal("5.000"),
        )

        # Intentamos eliminar el producto mediante POST
        response = self.client.post(reverse("productos:eliminar", kwargs={"pk": producto.pk}))
        self.assertRedirects(response, reverse("productos:listado"))

        # El producto no debe borrarse, debe quedar desactivado
        producto.refresh_from_db()
        self.assertFalse(producto.estado)

    def test_crud_categoria_marca_almacen_metodo_pago(self):
        """Valida que los nuevos CRUDs de Categoria, Marca, Almacén y Método de pago funcionen."""
        self.client.force_login(self.admin)

        # Crear Categoría
        resp_cat = self.client.post(reverse("productos:categoria_crear"), {
            "nombre": "Chocolates Gourmet",
            "descripcion": "Línea premium de cacao peruano",
            "estado": True,
        })
        self.assertRedirects(resp_cat, reverse("productos:categoria_listado"))
        self.assertTrue(Categoria.objects.filter(nombre="Chocolates Gourmet").exists())

        # Crear Marca
        resp_marca = self.client.post(reverse("productos:marca_crear"), {
            "nombre": "ChocoOro",
            "descripcion": "Marca propia",
            "estado": True,
        })
        self.assertRedirects(resp_marca, reverse("productos:marca_listado"))
        self.assertTrue(Marca.objects.filter(nombre="ChocoOro").exists())

        # Crear Almacén
        resp_alm = self.client.post(reverse("inventario:almacen_crear"), {
            "nombre": "Boutique Miraflores",
            "ubicacion": "Av. Larco 456",
            "descripcion": "Tienda y almacén boutique",
            "estado": True,
        })
        self.assertRedirects(resp_alm, reverse("inventario:almacen_listado"))
        self.assertTrue(Almacen.objects.filter(nombre="Boutique Miraflores").exists())

        # Crear Método de Pago
        resp_pago = self.client.post(reverse("configuracion:metodo_pago_crear"), {
            "nombre": "Billetera Digital",
            "descripcion": "Pagos QR",
            "estado": True,
        })
        self.assertRedirects(resp_pago, reverse("configuracion:metodo_pago_listado"))
        self.assertTrue(MetodoPago.objects.filter(nombre="Billetera Digital").exists())

    def test_pantalla_configuracion_negocio_singleton(self):
        """Valida la pantalla de configuración del negocio (registro único con logo e IGV)."""
        self.client.force_login(self.admin)

        # Acceder a la pantalla (GET)
        response_get = self.client.get(reverse("configuracion:inicio"))
        self.assertEqual(response_get.status_code, 200)
        self.assertContains(response_get, "Configuración del Negocio")

        # Modificar configuración (POST)
        response_post = self.client.post(reverse("configuracion:inicio"), {
            "nombre_negocio": "Chocolatería El Dorado SAC",
            "ruc": "20987654321",
            "direccion": "Calle Cacao 123",
            "telefono": "987654321",
            "email": "contacto@eldorado.pe",
            "porcentaje_igv": "18.00",
            "moneda": "PEN",
        })
        self.assertRedirects(response_post, reverse("configuracion:inicio"))

        config = Configuracion.objects.first()
        self.assertEqual(config.nombre_negocio, "Chocolatería El Dorado SAC")
        self.assertEqual(config.ruc, "20987654321")
        self.assertEqual(config.porcentaje_igv, Decimal("18.00"))

    def test_permisos_por_rol_en_vistas(self):
        """Valida que un Vendedor no pueda ingresar a Configuración ni a Almacenes."""
        self.client.force_login(self.vendedor)

        # Vendedor intentando acceder a Configuración -> redirige con mensaje
        resp_conf = self.client.get(reverse("configuracion:inicio"))
        self.assertRedirects(resp_conf, reverse("dashboard"))

        # Vendedor intentando acceder a Almacenes -> redirige con mensaje
        resp_alm = self.client.get(reverse("inventario:almacen_listado"))
        self.assertRedirects(resp_alm, reverse("dashboard"))

        # Vendedor accediendo a Clientes -> permitido (200)
        resp_cli = self.client.get(reverse("clientes:listado"))
        self.assertEqual(resp_cli.status_code, 200)

    def test_menu_lateral_segun_rol(self):
        """Verifica que el menú lateral muestre únicamente las opciones correspondientes a cada rol."""
        # Vendedor no debe ver enlaces a Usuarios, Finanzas o Configuración
        self.client.force_login(self.vendedor)
        resp_vendedor = self.client.get(reverse("dashboard"))
        self.assertNotContains(resp_vendedor, f'href="{reverse("usuarios:listado")}"')
        self.assertNotContains(resp_vendedor, reverse("configuracion:inicio"))
        self.assertNotContains(resp_vendedor, reverse("finanzas:inicio"))
        self.assertContains(resp_vendedor, reverse("clientes:listado"))

        # Administrador debe ver todos los enlaces
        self.client.force_login(self.admin)
        resp_admin = self.client.get(reverse("dashboard"))
        self.assertContains(resp_admin, reverse("usuarios:listado"))
        self.assertContains(resp_admin, reverse("configuracion:inicio"))
        self.assertContains(resp_admin, reverse("reportes:inicio"))
        self.assertContains(resp_admin, reverse("productos:listado"))

    def test_admin_transaccional_es_solo_lectura(self):
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        transaccionales = (
            Venta, DetalleVenta, PagoVenta, Compra, DetalleCompra, PagoCompra,
            Inventario, Lote, MovimientoInventario, Caja, MovimientoCaja,
            Devolucion, DetalleDevolucion, Gasto,
        )
        for modelo in transaccionales:
            with self.subTest(modelo=modelo.__name__):
                model_admin = admin.site._registry[modelo]
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request))
                self.assertFalse(model_admin.has_delete_permission(request))
                campos_lectura = set(model_admin.get_readonly_fields(request))
                self.assertTrue({campo.name for campo in modelo._meta.concrete_fields}.issubset(campos_lectura))
