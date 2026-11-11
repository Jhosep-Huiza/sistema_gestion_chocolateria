from apps.core.forms import BaseModelForm
from .models import Configuracion, MetodoPago

class ConfiguracionForm(BaseModelForm):
    class Meta:
        model = Configuracion
        fields = [
            "nombre_negocio", "ruc", "direccion", "telefono",
            "email", "logo", "porcentaje_igv", "moneda"
        ]


class MetodoPagoForm(BaseModelForm):
    class Meta:
        model = MetodoPago
        fields = ["nombre", "descripcion", "estado"]
