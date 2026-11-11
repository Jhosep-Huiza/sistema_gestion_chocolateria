from django.urls import reverse_lazy
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Cliente
from .forms import ClienteForm

class ClienteListView(BaseListView):
    model = Cliente
    titulo = "Cartera de Clientes"
    subtitulo = "Gestiona la información y datos de contacto de tus clientes frecuentes."
    search_fields = ["nombres", "numero_documento", "telefono", "email"]
    columnas = [
        {"campo": "tipo_documento", "titulo": "Tipo Doc."},
        {"campo": "numero_documento", "titulo": "N° Documento"},
        {"campo": "nombres", "titulo": "Nombres / Razón Social", "destacado": True},
        {"campo": "telefono", "titulo": "Teléfono"},
        {"campo": "email", "titulo": "Correo Electrónico"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "clientes:crear"
    url_editar = "clientes:editar"
    url_eliminar = "clientes:eliminar"
    roles_permitidos = ["Administrador", "Vendedor"]


class ClienteCreateView(BaseCreateView):
    model = Cliente
    form_class = ClienteForm
    titulo = "Nuevo Cliente"
    subtitulo = "Registra los datos de un nuevo cliente."
    success_url = reverse_lazy("clientes:listado")
    roles_permitidos = ["Administrador", "Vendedor"]


class ClienteUpdateView(BaseUpdateView):
    model = Cliente
    form_class = ClienteForm
    titulo = "Editar Cliente"
    subtitulo = "Actualiza la información del cliente."
    success_url = reverse_lazy("clientes:listado")
    roles_permitidos = ["Administrador", "Vendedor"]


class ClienteDeleteView(BaseDeleteView):
    model = Cliente
    success_url = reverse_lazy("clientes:listado")
    roles_permitidos = ["Administrador"]
