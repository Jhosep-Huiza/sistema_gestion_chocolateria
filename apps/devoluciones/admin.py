from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Devolucion, DetalleDevolucion


@admin.register(Devolucion)
class DevolucionAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("id", "venta", "fecha_devolucion", "usuario", "tipo_reembolso", "total_devolucion", "estado")
    list_filter = ("estado", "tipo_reembolso", "fecha_devolucion")
    search_fields = ("venta__numero_venta", "usuario__username", "motivo")
    list_select_related = ("venta", "usuario")
    date_hierarchy = "fecha_devolucion"


@admin.register(DetalleDevolucion)
class DetalleDevolucionAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("devolucion", "detalle_venta", "cantidad", "estado_producto")
    list_filter = ("estado_producto",)
    search_fields = ("devolucion__venta__numero_venta", "detalle_venta__producto__nombre")
    list_select_related = ("devolucion", "detalle_venta")
