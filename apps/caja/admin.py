from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Caja, MovimientoCaja


@admin.register(Caja)
class CajaAdmin(TransaccionSoloLecturaAdmin):
    list_display = (
        "id", "usuario", "fecha_apertura", "fecha_cierre", "estado",
        "monto_inicial", "monto_esperado", "monto_final", "diferencia",
    )
    list_filter = ("estado", "fecha_apertura", "fecha_cierre")
    search_fields = ("usuario__username", "usuario__nombres", "usuario__apellidos")
    list_select_related = ("usuario",)
    date_hierarchy = "fecha_apertura"


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("fecha", "caja", "tipo", "concepto", "monto", "usuario", "referencia_tipo")
    list_filter = ("tipo", "referencia_tipo", "fecha")
    search_fields = ("concepto", "usuario__username", "referencia_tipo")
    list_select_related = ("caja", "usuario")
    date_hierarchy = "fecha"
