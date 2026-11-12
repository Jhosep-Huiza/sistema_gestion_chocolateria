from apps.core.forms import BaseModelForm
from decimal import Decimal
from django import forms
from apps.core.forms import FormularioEstilizadoMixin
from django.utils import timezone
from .models import Almacen, Lote

class AlmacenForm(BaseModelForm):
    class Meta:
        model = Almacen
        fields = ["nombre", "ubicacion", "descripcion", "estado"]


class AjusteInventarioForm(FormularioEstilizadoMixin, forms.Form):
    lote = forms.ModelChoiceField(queryset=Lote.objects.none(), label="Lote")
    tipo = forms.ChoiceField(choices=[("POSITIVO", "Aumentar stock"), ("NEGATIVO", "Disminuir stock")], label="Tipo de ajuste")
    cantidad = forms.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), label="Cantidad")
    motivo = forms.CharField(max_length=255, label="Motivo", widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote"].queryset = Lote.objects.select_related("producto", "almacen").order_by("codigo_lote")


class TransferenciaStockForm(FormularioEstilizadoMixin, forms.Form):
    lote = forms.ModelChoiceField(queryset=Lote.objects.none(), label="Lote de origen")
    almacen_destino = forms.ModelChoiceField(queryset=Almacen.objects.none(), label="Almacén de destino")
    cantidad = forms.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), label="Cantidad")
    motivo = forms.CharField(max_length=255, label="Motivo", widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote"].queryset = Lote.objects.filter(
            estado="DISPONIBLE", cantidad_disponible__gt=0,
            fecha_vencimiento__gte=timezone.localdate(),
        ).select_related("producto", "almacen").order_by("codigo_lote")
        self.fields["almacen_destino"].queryset = Almacen.objects.filter(estado=True).order_by("nombre")


class EstadoLoteForm(FormularioEstilizadoMixin, forms.Form):
    estado = forms.ChoiceField(choices=[("CUARENTENA", "Poner en cuarentena"), ("DISPONIBLE", "Marcar disponible")], label="Nuevo estado")
