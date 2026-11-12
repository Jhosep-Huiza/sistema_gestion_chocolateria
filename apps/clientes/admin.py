from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombres", "tipo_documento", "numero_documento", "telefono", "email", "estado")
    list_filter = ("estado", "tipo_documento", "fecha_registro")
    search_fields = ("nombres", "numero_documento", "telefono", "email")
    readonly_fields = ("fecha_registro",)
