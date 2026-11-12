from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import DetalleVenta, PagoVenta, Venta


@admin.register(Venta)
class VentaAdmin(TransaccionSoloLecturaAdmin):
    readonly_fields = ("monto_pagado", "saldo_pendiente")
    list_display = (
        "numero_venta", "fecha_venta", "usuario", "cliente", "total", "estado",
        "monto_pagado", "saldo_pendiente",
    )
    list_filter = ("estado", "tipo_comprobante", "fecha_venta")
    search_fields = ("numero_venta", "numero_comprobante", "cliente__nombres", "usuario__username")
    list_select_related = ("cliente", "usuario", "caja")
    date_hierarchy = "fecha_venta"


@admin.register(DetalleVenta)
class DetalleVentaAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("venta", "producto", "lote", "cantidad", "precio_unitario", "descuento", "subtotal")
    list_filter = ("producto__categoria", "lote__almacen")
    search_fields = ("venta__numero_venta", "producto__codigo", "producto__nombre", "lote__codigo_lote")
    list_select_related = ("venta", "producto", "lote")


@admin.register(PagoVenta)
class PagoVentaAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("venta", "fecha_pago", "metodo_pago", "monto", "estado", "usuario")
    list_filter = ("estado", "metodo_pago", "fecha_pago")
    search_fields = ("venta__numero_venta", "referencia", "usuario__username")
    list_select_related = ("venta", "metodo_pago", "usuario")
