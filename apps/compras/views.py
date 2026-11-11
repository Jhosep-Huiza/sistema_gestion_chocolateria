from django.shortcuts import render
from apps.core.mixins import requiere_roles

@requiere_roles("Almacenero")
def inicio(request):
    return render(request, "modulo/en_construccion.html", {"titulo": "Compras"})
