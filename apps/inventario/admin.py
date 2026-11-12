from django.contrib import admin
from .models import Almacen, Inventario, Lote, MovimientoInventario

admin.site.register([Almacen, Lote, MovimientoInventario])


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("producto", "almacen", "stock_actual", "stock_reservado", "updated_at")
    list_select_related = ("producto", "almacen")
    readonly_fields = ("producto", "almacen", "stock_actual", "stock_reservado", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return False
