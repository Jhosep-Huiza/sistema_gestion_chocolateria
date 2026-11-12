from django.contrib import admin

from apps.core.admin import TransaccionSoloLecturaAdmin
from .models import Compra, DetalleCompra, PagoCompra


@admin.register(Compra)
class CompraAdmin(TransaccionSoloLecturaAdmin):
    readonly_fields = ("estado_pago", "monto_pagado", "saldo_pendiente")
    list_display = (
        "numero_compra", "fecha_compra", "proveedor", "usuario", "total", "estado",
        "estado_pago", "monto_pagado", "saldo_pendiente",
    )
    list_filter = ("estado", "tipo_documento", "fecha_compra")
    search_fields = ("numero_compra", "numero_documento", "proveedor__razon_social", "proveedor__ruc")
    list_select_related = ("proveedor", "usuario")
    date_hierarchy = "fecha_compra"


@admin.register(DetalleCompra)
class DetalleCompraAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("compra", "producto", "cantidad", "precio_unitario", "descuento", "subtotal")
    list_filter = ("producto__categoria",)
    search_fields = ("compra__numero_compra", "producto__codigo", "producto__nombre")
    list_select_related = ("compra", "producto")


@admin.register(PagoCompra)
class PagoCompraAdmin(TransaccionSoloLecturaAdmin):
    list_display = ("compra", "fecha_pago", "metodo_pago", "monto", "estado", "usuario")
    list_filter = ("estado", "metodo_pago", "fecha_pago")
    search_fields = ("compra__numero_compra", "referencia", "usuario__username")
    list_select_related = ("compra", "metodo_pago", "usuario")
