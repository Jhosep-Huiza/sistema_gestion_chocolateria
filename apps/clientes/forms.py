from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = "__all__"
        widgets = {field: forms.TextInput(attrs={"class":"form-control"}) for field in []}
