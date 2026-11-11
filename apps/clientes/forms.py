from apps.core.forms import BaseModelForm
from .models import Cliente

class ClienteForm(BaseModelForm):
    class Meta:
        model = Cliente
        fields = [
            "tipo_documento", "numero_documento", "nombres",
            "telefono", "email", "direccion", "estado"
        ]
