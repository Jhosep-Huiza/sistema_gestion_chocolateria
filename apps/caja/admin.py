from django.contrib import admin
from .models import Caja, MovimientoCaja

admin.site.register([Caja, MovimientoCaja])
