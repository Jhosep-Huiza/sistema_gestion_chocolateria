from django import forms
from apps.ventas.models import Venta
from .models import Devolucion, DetalleDevolucion


class SolicitudDevolucionForm(forms.Form):
    venta = forms.ModelChoiceField(queryset=Venta.objects.none(), label="Venta")
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"rows": 3}))
    tipo_reembolso = forms.ChoiceField(label="Tipo", choices=Devolucion.TIPOS)
    efectivo = forms.BooleanField(label="Reembolso en efectivo", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["venta"].queryset = Venta.objects.exclude(estado="ANULADA").order_by("-fecha_venta")


class RechazoDevolucionForm(forms.Form):
    motivo = forms.CharField(label="Motivo del rechazo", required=False, max_length=255)


class DetalleDevolucionForm(forms.Form):
    detalle_venta_id = forms.IntegerField(widget=forms.HiddenInput)
    cantidad = forms.DecimalField(label="Cantidad", required=False, min_value=0.001, decimal_places=3, max_digits=12)
    estado_producto = forms.ChoiceField(label="Estado del producto", choices=DetalleDevolucion.ESTADOS_PRODUCTO)
