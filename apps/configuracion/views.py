from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from apps.core.mixins import PermisoRolMixin
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Configuracion, MetodoPago
from .forms import ConfiguracionForm, MetodoPagoForm

# ==========================================
# CONFIGURACIÓN DEL NEGOCIO (REGISTRO ÚNICO)
# ==========================================

class ConfiguracionNegocioView(LoginRequiredMixin, PermisoRolMixin, View):
    """
    Pantalla de configuración del negocio (registro único):
    Control de nombre, RUC, logo, porcentaje de IGV y moneda.
    """
    roles_permitidos = ["Administrador"]
    template_name = "modulo/formulario.html"

    def get_object(self):
        config = Configuracion.objects.first()
        if not config:
            config = Configuracion(
                nombre_negocio="ChocoGest",
                porcentaje_igv="18.00",
                moneda="PEN",
            )
        return config

    def get(self, request, *args, **kwargs):
        config = self.get_object()
        form = ConfiguracionForm(instance=config)
        return render(request, self.template_name, {
            "form": form,
            "titulo": "Configuración del Negocio",
            "subtitulo": "Administra la identidad comercial, tasas de impuestos y moneda de la chocolatería.",
            "url_cancelar": reverse_lazy("dashboard"),
        })

    def post(self, request, *args, **kwargs):
        config = self.get_object()
        form = ConfiguracionForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración del negocio guardada correctamente.")
            return redirect("configuracion:inicio")
        return render(request, self.template_name, {
            "form": form,
            "titulo": "Configuración del Negocio",
            "subtitulo": "Administra la identidad comercial, tasas de impuestos y moneda de la chocolatería.",
            "url_cancelar": reverse_lazy("dashboard"),
        })


# ==========================================
# CRUD MÉTODOS DE PAGO
# ==========================================

class MetodoPagoListView(BaseListView):
    model = MetodoPago
    titulo = "Métodos de Pago"
    subtitulo = "Gestiona las opciones de cobro disponibles en caja y ventas."
    search_fields = ["nombre", "descripcion"]
    columnas = [
        {"campo": "nombre", "titulo": "Nombre", "destacado": True},
        {"campo": "descripcion", "titulo": "Descripción"},
        {"campo": "estado", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "configuracion:metodo_pago_crear"
    url_editar = "configuracion:metodo_pago_editar"
    url_eliminar = "configuracion:metodo_pago_eliminar"
    roles_permitidos = ["Administrador"]


class MetodoPagoCreateView(BaseCreateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    titulo = "Nuevo Método de Pago"
    subtitulo = "Registra una forma de pago válida en el sistema."
    success_url = reverse_lazy("configuracion:metodo_pago_listado")
    roles_permitidos = ["Administrador"]


class MetodoPagoUpdateView(BaseUpdateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    titulo = "Editar Método de Pago"
    subtitulo = "Actualiza la información del método de pago."
    success_url = reverse_lazy("configuracion:metodo_pago_listado")
    roles_permitidos = ["Administrador"]


class MetodoPagoDeleteView(BaseDeleteView):
    model = MetodoPago
    success_url = reverse_lazy("configuracion:metodo_pago_listado")
    roles_permitidos = ["Administrador"]
