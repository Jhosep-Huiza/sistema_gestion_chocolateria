from django.contrib import admin
from .models import Devolucion, DetalleDevolucion

admin.site.register([Devolucion, DetalleDevolucion])
