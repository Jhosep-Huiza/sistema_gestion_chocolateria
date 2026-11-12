from django.contrib import admin
from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "ruc", "contacto", "telefono", "email", "estado")
    list_filter = ("estado",)
    search_fields = ("razon_social", "ruc", "contacto", "telefono", "email")
