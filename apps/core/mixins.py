from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

class PermisoRolMixin:
    """
    Mixin para restringir el acceso a vistas según el rol del usuario en ChocoGest.
    - Superusuarios siempre tienen acceso total.
    - Si roles_permitidos es None o vacío, cualquier usuario autenticado tiene acceso.
    - Si el usuario no tiene el rol requerido, se le notifica y redirige al dashboard.
    """
    roles_permitidos = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if self.roles_permitidos:
            rol_actual = getattr(request.user.rol, "nombre", None) if getattr(request.user, "rol", None) else None
            if rol_actual not in self.roles_permitidos:
                messages.error(request, "Acceso restringido: no tienes permisos para acceder a esta sección.")
                return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)


def requiere_roles(*roles):
    """Restringe una vista autenticada a los roles indicados; Admin siempre accede."""
    def decorador(vista):
        @wraps(vista)
        def protegida(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            rol = getattr(getattr(request.user, "rol", None), "nombre", None)
            if request.user.is_superuser or rol == "Administrador" or rol in roles:
                return vista(request, *args, **kwargs)
            messages.error(request, "Acceso restringido: tu rol no permite realizar esta acción.")
            return redirect("dashboard")
        return protegida
    return decorador


class MensajeCrudMixin:
    """
    Mixin para estandarizar mensajes de éxito tras crear o actualizar un registro.
    """
    success_message = "Operación realizada con éxito."

    def get_success_message(self, cleaned_data):
        return self.success_message

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.get_success_message(form.cleaned_data))
        return response
