from django.urls import reverse_lazy
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Proveedor
from .forms import ProveedorForm

class ProveedorListView(BaseListView):
    model = Proveedor
    titulo = "Registro de Proveedores"
    subtitulo = "Gestiona los proveedores de cacao, empaques e insumos chocolateros."
    search_fields = ["razon_social", "ruc", "contacto", "telefono", "email"]
    columnas = [
        {"campo": "ruc", "titulo": "RUC"},
        {"campo": "razon_social", "titulo": "Razón Social", "destacado": True},
        {"campo": "contacto", "titulo": "Persona de Contacto"},
        {"campo": "telefono", "titulo": "Teléfono"},
        {"campo": "email", "titulo": "Correo Electrónico"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "proveedores:crear"
    url_editar = "proveedores:editar"
    url_eliminar = "proveedores:eliminar"
    roles_permitidos = ["Administrador", "Almacenero"]


class ProveedorCreateView(BaseCreateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Nuevo Proveedor"
    subtitulo = "Registra los datos de un nuevo proveedor comercial."
    success_url = reverse_lazy("proveedores:listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class ProveedorUpdateView(BaseUpdateView):
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Editar Proveedor"
    subtitulo = "Actualiza la información comercial del proveedor."
    success_url = reverse_lazy("proveedores:listado")
    roles_permitidos = ["Administrador", "Almacenero"]


class ProveedorDeleteView(BaseDeleteView):
    model = Proveedor
    success_url = reverse_lazy("proveedores:listado")
    roles_permitidos = ["Administrador"]
