from decimal import Decimal
from django import forms
from apps.core.forms import FormularioEstilizadoMixin
from apps.configuracion.models import MetodoPago


class PagoVentaForm(FormularioEstilizadoMixin, forms.Form):
    metodo_pago = forms.ModelChoiceField(queryset=MetodoPago.objects.none(), label="Método de pago")
    monto = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), label="Monto")
    referencia = forms.CharField(max_length=100, required=False, label="Referencia")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["metodo_pago"].queryset = MetodoPago.objects.filter(estado=True).order_by("nombre")


class AnularVentaForm(FormularioEstilizadoMixin, forms.Form):
    motivo = forms.CharField(max_length=255, label="Motivo de anulación", widget=forms.Textarea)
