from django import forms

from apps.productos.models import Producto
from apps.usuarios.models import Usuario


class FiltroReporteForm(forms.Form):
    desde = forms.DateField(label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    vendedor = forms.ModelChoiceField(
        label="Vendedor", queryset=Usuario.objects.none(), required=False,
        empty_label="Todos los vendedores",
    )
    producto = forms.ModelChoiceField(
        label="Producto", queryset=Producto.objects.none(), required=False,
        empty_label="Todos los productos",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendedor"].queryset = Usuario.objects.filter(ventas__isnull=False).distinct().order_by("username")
        self.fields["producto"].queryset = Producto.objects.order_by("nombre")

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha inicial no puede ser posterior a la fecha final.")
        return datos
