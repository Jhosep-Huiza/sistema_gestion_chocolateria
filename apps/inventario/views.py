from django.shortcuts import render
from apps.core.mixins import requiere_roles
from django.urls import reverse_lazy
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Almacen
from .forms import AlmacenForm

@requiere_roles("Almacenero")
def inicio(request):
    return render(request, "modulo/en_construccion.html", {"titulo": "Inventario"})


# ==========================================
# CRUD ALMACENES
# ==========================================

class AlmacenListView(BaseListView):
    model = Almacen
    titulo = "Almacenes y Ubicaciones"
    subtitulo = "Controla los espacios físicos de almacenamiento y tiendas."
    search_fields = ["nombre", "ubicacion", "descripcion"]
    columnas = [
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "ubicacion", "titulo": "Ubicación"},
        {"campo": "descripcion", "titulo": "Descripción"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "inventario:almacen_crear"
    url_editar = "inventario:almacen_editar"
    url_eliminar = "inventario:almacen_eliminar"
    roles_permitidos = ["Administrador", "Almacenero"]
    roles_crear = ["Administrador"]
    roles_editar = ["Administrador"]


class AlmacenCreateView(BaseCreateView):
    model = Almacen
    form_class = AlmacenForm
    titulo = "Nuevo Almacén"
    subtitulo = "Registra una nueva bodega o punto de venta."
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]


class AlmacenUpdateView(BaseUpdateView):
    model = Almacen
    form_class = AlmacenForm
    titulo = "Editar Almacén"
    subtitulo = "Modifica los datos del almacén seleccionado."
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]


class AlmacenDeleteView(BaseDeleteView):
    model = Almacen
    success_url = reverse_lazy("inventario:almacen_listado")
    roles_permitidos = ["Administrador"]
