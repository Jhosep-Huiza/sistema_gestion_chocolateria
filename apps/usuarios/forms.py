from django import forms
from apps.core.forms import BaseModelForm
from apps.core.forms import FormularioEstilizadoMixin
from django.contrib.auth.forms import PasswordChangeForm
from .models import Usuario

class UsuarioCrearForm(BaseModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Contraseña segura"}),
        required=True
    )

    class Meta:
        model = Usuario
        fields = [
            "username", "password", "nombres", "apellidos",
            "email", "telefono", "rol", "is_active"
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UsuarioEditarForm(BaseModelForm):
    password = forms.CharField(
        label="Nueva contraseña (opcional)",
        widget=forms.PasswordInput(attrs={"placeholder": "Dejar en blanco para conservar la actual"}),
        required=False
    )

    class Meta:
        model = Usuario
        fields = [
            "username", "nombres", "apellidos",
            "email", "telefono", "rol", "is_active", "password"
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class MiCambioContrasenaForm(FormularioEstilizadoMixin, PasswordChangeForm):
    """Formulario para que cada usuario cambie su propia contraseña."""
