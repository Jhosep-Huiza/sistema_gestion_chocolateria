from django.contrib import admin
from .models import Compra, DetalleCompra, PagoCompra

admin.site.register([Compra, DetalleCompra, PagoCompra])
