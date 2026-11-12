from django import forms


class AperturaCajaForm(forms.Form):
    monto_inicial = forms.DecimalField(label="Monto inicial", min_value=0, decimal_places=2, max_digits=12)


class MovimientoCajaForm(forms.Form):
    TIPOS = [("INGRESO", "Ingreso"), ("EGRESO", "Egreso")]
    tipo = forms.ChoiceField(label="Tipo", choices=TIPOS)
    concepto = forms.CharField(label="Concepto", max_length=150)
    monto = forms.DecimalField(label="Monto", min_value="0.01", decimal_places=2, max_digits=12)


class CierreCajaForm(forms.Form):
    monto_final = forms.DecimalField(label="Monto contado", min_value=0, decimal_places=2, max_digits=12)
