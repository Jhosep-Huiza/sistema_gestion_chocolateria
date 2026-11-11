from apps.core.forms import BaseModelForm
from .models import Proveedor

class ProveedorForm(BaseModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "ruc", "razon_social", "contacto", "telefono",
            "email", "direccion", "estado"
        ]
