from django.contrib import admin
from .models import Configuracion, MetodoPago


@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ("nombre_negocio", "ruc", "moneda", "porcentaje_igv", "updated_at")
    search_fields = ("nombre_negocio", "ruc", "email")
    readonly_fields = ("updated_at",)


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")
