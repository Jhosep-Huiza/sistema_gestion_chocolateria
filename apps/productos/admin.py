from django.contrib import admin
from .models import Categoria, Marca, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre", "descripcion")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "nombre", "categoria", "marca", "precio_compra_referencial",
        "precio_venta", "stock_minimo", "estado",
    )
    list_filter = ("estado", "categoria", "marca")
    search_fields = ("codigo", "codigo_barras", "nombre", "descripcion")
    list_select_related = ("categoria", "marca")
    readonly_fields = ("created_at", "updated_at")
