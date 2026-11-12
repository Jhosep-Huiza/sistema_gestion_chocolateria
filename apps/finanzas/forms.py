from django import forms
from apps.caja.models import Caja
from .models import Gasto


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ["categoria", "descripcion", "monto", "fecha_gasto", "comprobante", "es_efectivo", "caja"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_gasto": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M",
            ),
            "monto": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_gasto"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["caja"].required = False
        self.fields["caja"].queryset = Caja.objects.filter(estado="ABIERTA").order_by("-fecha_apertura")
        self.fields["caja"].label = "Caja abierta (para gasto en efectivo)"
        self.fields["es_efectivo"].label = "Pagado en efectivo"


class PeriodoFinancieroForm(forms.Form):
    desde = forms.DateField(label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha inicial no puede ser posterior a la fecha final.")
        return datos
