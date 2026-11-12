from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Almacen, Inventario, Lote, MovimientoInventario


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "ubicacion", "descripcion")


@admin.register(Inventario)
class InventarioAdmin(TransaccionSoloLecturaAdmin):
    readonly_fields = ("estado_stock",)
    list_display = ("producto", "almacen", "stock_actual", "stock_reservado", "estado_stock", "updated_at")
    list_filter = ("almacen", "producto__categoria")
    search_fields = ("producto__codigo", "producto__nombre", "almacen__nombre")
    list_select_related = ("producto", "almacen")


@admin.register(Lote)
class LoteAdmin(TransaccionSoloLecturaAdmin):
    list_display = (
        "codigo_lote", "producto", "almacen", "fecha_vencimiento",
        "cantidad_disponible", "estado",
    )
    list_filter = ("estado", "almacen", "fecha_vencimiento", "producto__categoria")
    search_fields = ("codigo_lote", "producto__codigo", "producto__nombre")
    list_select_related = ("producto", "almacen", "detalle_compra")
    date_hierarchy = "fecha_vencimiento"


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("fecha", "tipo_movimiento", "producto", "almacen", "lote", "cantidad", "usuario")
    list_filter = ("tipo_movimiento", "almacen", "fecha")
    search_fields = ("producto__codigo", "producto__nombre", "lote__codigo_lote", "motivo")
    list_select_related = ("producto", "almacen", "lote", "usuario")
    date_hierarchy = "fecha"
