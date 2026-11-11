from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = "__all__"
        widgets = {field: forms.TextInput(attrs={"class":"form-control"}) for field in []}
