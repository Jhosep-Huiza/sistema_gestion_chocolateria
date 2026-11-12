from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.inventario.models import Almacen, Inventario
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario
from apps.ventas.models import Venta
from .services import construir_reporte


class ReportesTest(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre="Administrador")
        self.admin = Usuario.objects.create_user(username="admin_reportes", password="pass", rol=rol)
        self.cliente = Client()
        self.cliente.force_login(self.admin)

    def test_dashboard_calcula_stock_bajo_contra_minimo_en_cada_almacen(self):
        categoria = Categoria.objects.create(nombre="Tabletas")
        almacena = Almacen.objects.create(nombre="Principal")
        almacena_dos = Almacen.objects.create(nombre="Tienda")
        producto_normal = Producto.objects.create(
            categoria=categoria, codigo="REP-NOR", nombre="Stock normal",
            precio_venta=Decimal("10.00"), stock_minimo=Decimal("5.000"),
        )
        producto_bajo = Producto.objects.create(
            categoria=categoria, codigo="REP-BAJ", nombre="Stock bajo",
            precio_venta=Decimal("10.00"), stock_minimo=Decimal("5.000"),
        )
        Inventario.objects.create(producto=producto_normal, almacen=almacena, stock_actual=Decimal("3.000"))
        Inventario.objects.create(producto=producto_normal, almacen=almacena_dos, stock_actual=Decimal("3.000"))
        Inventario.objects.create(producto=producto_bajo, almacen=almacena, stock_actual=Decimal("4.000"))
        Venta.objects.create(
            usuario=self.admin, numero_venta="VTA-REP-DASH",
            fecha_venta=timezone.make_aware(datetime.combine(timezone.localdate(), time(12))),
            total=Decimal("25.00"), estado="PAGADA",
        )
        respuesta = self.cliente.get(reverse("dashboard"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["stock_bajo"], 2)
        self.assertEqual(respuesta.context["ventas_hoy"], Decimal("25.00"))
        self.assertEqual(respuesta.context["ventas_ultimos_siete"][-1]["total"], Decimal("25.00"))

    def test_todos_los_reportes_muestran_html_y_exportan_csv_excel(self):
        categoria = Categoria.objects.create(nombre="Muestra")
        almacen = Almacen.objects.create(nombre="Principal")
        producto = Producto.objects.create(
            categoria=categoria, codigo="REP-XLS", nombre="Producto valorizado",
            precio_venta=Decimal("10.00"), precio_compra_referencial=Decimal("2.15"),
        )
        Inventario.objects.create(producto=producto, almacen=almacen, stock_actual=Decimal("3.000"))
        self.assertEqual(self.cliente.get(reverse("reportes:inicio")).status_code, 200)
        claves = ["ventas", "compras", "inventario", "lotes", "mas_vendidos", "cajas"]
        for clave in claves:
            with self.subTest(reporte=clave):
                respuesta_html = self.cliente.get(reverse("reportes:reporte", args=[clave]))
                self.assertEqual(respuesta_html.status_code, 200)
                self.assertContains(respuesta_html, "Exportar Excel")
                respuesta_csv = self.cliente.get(reverse("reportes:exportar", args=[clave, "csv"]))
                self.assertEqual(respuesta_csv.status_code, 200)
                self.assertIn("text/csv", respuesta_csv["Content-Type"])
                respuesta_excel = self.cliente.get(reverse("reportes:exportar", args=[clave, "excel"]))
                self.assertEqual(respuesta_excel.status_code, 200)
                libro = load_workbook(filename=BytesIO(respuesta_excel.content), read_only=True)
                self.assertGreaterEqual(libro.active.max_column, 1)
                if clave == "inventario":
                    self.assertEqual(libro.active.cell(row=2, column=8).value, 6.45)

    def test_filtros_por_fecha_vendedor_y_producto_se_aplican_en_ventas(self):
        categoria = Categoria.objects.create(nombre="Trufas")
        producto = Producto.objects.create(
            categoria=categoria, codigo="REP-FIL", nombre="Trufa", precio_venta=Decimal("5.00"),
        )
        desde = timezone.localdate() - timedelta(days=1)
        titulo, columnas, filas = construir_reporte(
            clave="ventas", desde=desde, hasta=timezone.localdate(),
            vendedor_id=self.admin.pk, producto_id=producto.pk,
        )
        self.assertEqual(titulo, "Ventas por vendedor y producto")
        self.assertEqual(columnas[0], "Vendedor")
        self.assertEqual(filas, [])
