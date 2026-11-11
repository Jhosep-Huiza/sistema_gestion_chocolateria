from django.contrib import admin
from .models import Almacen, Inventario, Lote, MovimientoInventario

admin.site.register([Almacen, Inventario, Lote, MovimientoInventario])
