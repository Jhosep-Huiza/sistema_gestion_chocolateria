from django.urls import reverse_lazy
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Producto, Categoria, Marca
from .forms import ProductoForm, CategoriaForm, MarcaForm
from apps.usuarios.services import registrar_auditoria, obtener_ip

# ==========================================
# CRUD PRODUCTOS
# ==========================================

class ProductoListView(BaseListView):
    model = Producto
    titulo = "Catálogo de Productos"
    subtitulo = "Gestiona los chocolates y artículos disponibles para venta y producción."
    search_fields = ["codigo", "nombre", "descripcion", "codigo_barras"]
    columnas = [
        {"campo": "codigo", "titulo": "Código"},
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "categoria.nombre", "titulo": "Categoría"},
        {"campo": "marca.nombre", "titulo": "Marca"},
        {"campo": "precio_venta", "titulo": "Precio Venta", "tipo": "moneda"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "productos:crear"
    url_editar = "productos:editar"
    url_eliminar = "productos:eliminar"
    roles_permitidos = ["Administrador", "Vendedor", "Almacenero"]
    roles_crear = ["Administrador", "Almacenero"]
    roles_editar = ["Administrador", "Almacenero"]


class ProductoCreateView(BaseCreateView):
    model = Producto
    form_class = ProductoForm
    titulo = "Nuevo Producto"
    subtitulo = "Registra un nuevo chocolate o producto en el catálogo."
    success_url = reverse_lazy("productos:listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class ProductoUpdateView(BaseUpdateView):
    model = Producto
    form_class = ProductoForm
    titulo = "Editar Producto"
    subtitulo = "Actualiza los datos del producto seleccionado."
    success_url = reverse_lazy("productos:listado")
    roles_permitidos = ["Administrador", "Almacenero"]

    def form_valid(self, form):
        precio_anterior = self.get_object().precio_venta
        response = super().form_valid(form)
        if precio_anterior != self.object.precio_venta:
            registrar_auditoria(usuario=self.request.user, accion="CAMBIO_PRECIO",
                                tabla_afectada="productos", registro_id=self.object.pk,
                                descripcion=f"Precio de venta: {precio_anterior} → {self.object.precio_venta}.",
                                direccion_ip=obtener_ip(self.request))
        return response


class ProductoDeleteView(BaseDeleteView):
    model = Producto
    success_url = reverse_lazy("productos:listado")
    roles_permitidos = ["Administrador"]


# ==========================================
# CRUD CATEGORÍAS
# ==========================================

class CategoriaListView(BaseListView):
    model = Categoria
    titulo = "Categorías de Chocolates"
    subtitulo = "Agrupa los productos por líneas y variedades (tabletas, bombones, trufas, etc.)."
    search_fields = ["nombre", "descripcion"]
    columnas = [
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "descripcion", "titulo": "Descripción"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "productos:categoria_crear"
    url_editar = "productos:categoria_editar"
    url_eliminar = "productos:categoria_eliminar"
    roles_permitidos = ["Administrador", "Almacenero"]


class CategoriaCreateView(BaseCreateView):
    model = Categoria
    form_class = CategoriaForm
    titulo = "Nueva Categoría"
    subtitulo = "Crea una categoría para clasificar tus productos."
    success_url = reverse_lazy("productos:categoria_listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class CategoriaUpdateView(BaseUpdateView):
    model = Categoria
    form_class = CategoriaForm
    titulo = "Editar Categoría"
    subtitulo = "Actualiza los datos de la categoría."
    success_url = reverse_lazy("productos:categoria_listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class CategoriaDeleteView(BaseDeleteView):
    model = Categoria
    success_url = reverse_lazy("productos:categoria_listado")
    roles_permitidos = ["Administrador"]


# ==========================================
# CRUD MARCAS
# ==========================================

class MarcaListView(BaseListView):
    model = Marca
    titulo = "Marcas de Productos"
    subtitulo = "Gestiona las marcas comerciales de los insumos y chocolates."
    search_fields = ["nombre", "descripcion"]
    columnas = [
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "descripcion", "titulo": "Descripción"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "productos:marca_crear"
    url_editar = "productos:marca_editar"
    url_eliminar = "productos:marca_eliminar"
    roles_permitidos = ["Administrador", "Almacenero"]


class MarcaCreateView(BaseCreateView):
    model = Marca
    form_class = MarcaForm
    titulo = "Nueva Marca"
    subtitulo = "Registra una nueva marca de producto."
    success_url = reverse_lazy("productos:marca_listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class MarcaUpdateView(BaseUpdateView):
    model = Marca
    form_class = MarcaForm
    titulo = "Editar Marca"
    subtitulo = "Modifica los datos de la marca."
    success_url = reverse_lazy("productos:marca_listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class MarcaDeleteView(BaseDeleteView):
    model = Marca
    success_url = reverse_lazy("productos:marca_listado")
    roles_permitidos = ["Administrador"]
