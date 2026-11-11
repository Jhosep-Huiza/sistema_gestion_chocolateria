from apps.core.forms import BaseModelForm
from .models import Almacen

class AlmacenForm(BaseModelForm):
    class Meta:
        model = Almacen
        fields = ["nombre", "ubicacion", "descripcion", "estado"]
