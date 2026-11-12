from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Gasto


@admin.register(Gasto)
class GastoAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("fecha_gasto", "categoria", "monto", "es_efectivo", "caja", "estado", "usuario")
    list_filter = ("estado", "es_efectivo", "categoria", "fecha_gasto")
    search_fields = ("categoria", "descripcion", "usuario__username")
    list_select_related = ("caja", "usuario")
    date_hierarchy = "fecha_gasto"
