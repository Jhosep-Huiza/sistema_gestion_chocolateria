from django.contrib import admin
from .models import Configuracion, MetodoPago

admin.site.register([Configuracion, MetodoPago])
