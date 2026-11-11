from django.contrib import admin
from .models import Categoria, Marca, Producto

admin.site.register([Categoria, Marca, Producto])
