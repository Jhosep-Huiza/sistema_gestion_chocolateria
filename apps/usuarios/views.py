from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.http import url_has_allowed_host_and_scheme
from apps.core.views import BaseListView, BaseCreateView, BaseUpdateView, BaseDeleteView
from .models import Usuario
from .forms import UsuarioCrearForm, UsuarioEditarForm
from .forms import MiCambioContrasenaForm
from .services import registrar_auditoria, obtener_ip
from apps.core.mixins import PermisoRolMixin

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            registrar_auditoria(usuario=user, accion="LOGIN", tabla_afectada="usuarios",
                                registro_id=user.pk, direccion_ip=obtener_ip(request))
            next_url = request.POST.get("next") or request.GET.get("next")
            if not next_url or not url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = "dashboard"
            return redirect(next_url)
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "auth/login.html")

@login_required
@require_POST
def logout_view(request):
    usuario = request.user
    registrar_auditoria(usuario=usuario, accion="LOGOUT", tabla_afectada="usuarios",
                        registro_id=getattr(usuario, "pk", None), direccion_ip=obtener_ip(request))
    logout(request)
    return redirect("login")


# ==========================================
# CRUD USUARIOS (ADMINISTRACIÓN)
# ==========================================

class UsuarioListView(BaseListView):
    model = Usuario
    titulo = "Gestión de Usuarios"
    subtitulo = "Administra las cuentas de acceso del personal, cajeros y administradores."
    search_fields = ["username", "nombres", "apellidos", "email"]
    columnas = [
        {"campo": "username", "titulo": "Usuario", "destacado": True},
        {"campo": "get_full_name", "titulo": "Nombre Completo"},
        {"campo": "rol.nombre", "titulo": "Rol"},
        {"campo": "email", "titulo": "Correo Electrónico"},
        {"campo": "is_active", "titulo": "Estado", "tipo": "badge"},
    ]
    url_crear = "usuarios:crear"
    url_editar = "usuarios:editar"
    url_eliminar = "usuarios:eliminar"
    url_estado = "usuarios:estado"
    roles_permitidos = ["Administrador"]


class UsuarioCreateView(BaseCreateView):
    model = Usuario
    form_class = UsuarioCrearForm
    titulo = "Nuevo Usuario"
    subtitulo = "Registra una cuenta de usuario con credenciales y rol asignado."
    success_url = reverse_lazy("usuarios:listado")
    roles_permitidos = ["Administrador"]


class UsuarioUpdateView(BaseUpdateView):
    model = Usuario
    form_class = UsuarioEditarForm
    titulo = "Editar Usuario"
    subtitulo = "Actualiza los datos personales, rol o credenciales del usuario."
    success_url = reverse_lazy("usuarios:listado")
    roles_permitidos = ["Administrador"]

    def form_valid(self, form):
        rol_anterior = self.get_object().rol_id
        cambio_contrasena = bool(form.cleaned_data.get("password"))
        response = super().form_valid(form)
        if rol_anterior != self.object.rol_id:
            registrar_auditoria(usuario=self.request.user, accion="CAMBIO_ROL",
                                tabla_afectada="usuarios", registro_id=self.object.pk,
                                descripcion=f"Rol actualizado a {self.object.rol}.",
                                direccion_ip=obtener_ip(self.request))
        if cambio_contrasena:
            registrar_auditoria(usuario=self.request.user, accion="CAMBIO_CONTRASENA",
                                tabla_afectada="usuarios", registro_id=self.object.pk,
                                direccion_ip=obtener_ip(self.request))
        return response


class UsuarioDeleteView(BaseDeleteView):
    model = Usuario
    success_url = reverse_lazy("usuarios:listado")
    roles_permitidos = ["Administrador"]


class UsuarioEstadoView(LoginRequiredMixin, PermisoRolMixin, View):
    """Activa o desactiva una cuenta mediante una petición POST."""
    roles_permitidos = ["Administrador"]

    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
        else:
            usuario.is_active = not usuario.is_active
            usuario.save(update_fields=["is_active"])
            estado = "activada" if usuario.is_active else "desactivada"
            messages.success(request, f"La cuenta de {usuario.username} fue {estado}.")
            registrar_auditoria(usuario=request.user, accion="CAMBIO_ESTADO_USUARIO",
                                tabla_afectada="usuarios", registro_id=usuario.pk,
                                descripcion=f"Cuenta {estado}.", direccion_ip=obtener_ip(request))
        return redirect("usuarios:listado")


class MiPerfilView(LoginRequiredMixin, View):
    """Permite al usuario cambiar su propia contraseña."""
    template_name = "modulo/formulario.html"

    def get(self, request):
        return render(request, self.template_name, {
            "titulo": "Mi perfil", "subtitulo": "Actualiza tu contraseña de acceso.",
            "form": MiCambioContrasenaForm(request.user),
            "url_cancelar": reverse_lazy("dashboard"),
        })

    def post(self, request):
        form = MiCambioContrasenaForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu contraseña se actualizó correctamente.")
            registrar_auditoria(usuario=request.user, accion="CAMBIO_CONTRASENA_PROPIA",
                                tabla_afectada="usuarios", registro_id=request.user.pk,
                                direccion_ip=obtener_ip(request))
            return redirect("usuarios:perfil")
        return render(request, self.template_name, {
            "titulo": "Mi perfil", "subtitulo": "Actualiza tu contraseña de acceso.",
            "form": form, "url_cancelar": reverse_lazy("dashboard"),
        })
