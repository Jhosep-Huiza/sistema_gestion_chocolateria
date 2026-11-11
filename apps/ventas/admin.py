from django.contrib import admin
from .models import Venta, DetalleVenta, PagoVenta

admin.site.register([Venta, DetalleVenta, PagoVenta])
