from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, ProtectedError, RestrictedError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from .mixins import PermisoRolMixin, MensajeCrudMixin

class BaseListView(LoginRequiredMixin, PermisoRolMixin, ListView):
    """
    Vista base para listados en ChocoGest:
    - Paginación obligatoria (20 registros por página).
    - Búsqueda genérica por los campos definidos en search_fields.
    - Metadatos de columnas, permisos y URLs unificadas.
    """
    paginate_by = 20
    template_name = "modulo/listado.html"
    context_object_name = "registros"
    titulo = "Listado"
    subtitulo = "Administra la información registrada en el sistema."
    columnas = []
    search_fields = []
    url_crear = None
    url_editar = None
    url_eliminar = None
    url_estado = None
    placeholder_buscar = "Buscar por nombre, código o descripción..."

    def get_queryset(self):
        qs = super().get_queryset()
        if not qs.ordered:
            qs = qs.order_by("pk")
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["subtitulo"] = self.subtitulo
        context["columnas"] = self.columnas
        context["q"] = self.request.GET.get("q", "").strip()
        context["url_crear"] = self.url_crear
        context["url_editar"] = self.url_editar
        context["url_eliminar"] = self.url_eliminar
        context["url_estado"] = self.url_estado
        context["placeholder_buscar"] = self.placeholder_buscar
        def tiene_permiso(roles):
            if self.request.user.is_superuser:
                return True
            if roles is None:
                roles = self.roles_permitidos
            if not roles:
                return True
            rol = getattr(getattr(self.request.user, "rol", None), "nombre", None)
            return rol in roles

        context["permiso_crear"] = tiene_permiso(getattr(self, "roles_crear", None))
        context["permiso_editar"] = tiene_permiso(getattr(self, "roles_editar", None))
        context["permiso_eliminar"] = tiene_permiso(
            getattr(self, "roles_eliminar", None) or ["Administrador"]
        )
        return context


class BaseCreateView(LoginRequiredMixin, PermisoRolMixin, MensajeCrudMixin, CreateView):
    """
    Vista base para creación de registros con validación de formularios y mensajes amables.
    """
    template_name = "modulo/formulario.html"
    titulo = "Nuevo registro"
    subtitulo = "Completa los campos del formulario."
    success_message = "Registro creado correctamente."
    url_cancelar = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["subtitulo"] = self.subtitulo
        context["url_cancelar"] = self.url_cancelar or (self.success_url if isinstance(self.success_url, str) else None)
        return context


class BaseUpdateView(LoginRequiredMixin, PermisoRolMixin, MensajeCrudMixin, UpdateView):
    """
    Vista base para edición de registros existentes.
    """
    template_name = "modulo/formulario.html"
    titulo = "Editar registro"
    subtitulo = "Modifica los campos necesarios del formulario."
    success_message = "Registro actualizado correctamente."
    url_cancelar = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["subtitulo"] = self.subtitulo
        context["url_cancelar"] = self.url_cancelar or (self.success_url if isinstance(self.success_url, str) else None)
        return context


class BaseDeleteView(LoginRequiredMixin, PermisoRolMixin, View):
    """
    Vista base para eliminación segura de registros:
    - Exige método POST con CSRF para ejecutar la acción de borrado.
    - Captura ProtectedError/RestrictedError: si el objeto tiene 'estado', lo desactiva (estado=False)
      para proteger el historial y emite una advertencia amable.
    """
    model = None
    template_name = "modulo/confirmar_eliminar.html"
    titulo = "Confirmar eliminación"
    success_url = None
    url_cancelar = None

    def get_object(self):
        pk = self.kwargs.get("pk")
        return get_object_or_404(self.model, pk=pk)

    def get_success_url(self):
        if not self.success_url:
            raise NotImplementedError("Debes definir success_url en BaseDeleteView.")
        return str(self.success_url)

    def get(self, request, *args, **kwargs):
        objeto = self.get_object()
        return render(request, self.template_name, {
            "objeto": objeto,
            "titulo": self.titulo,
            "url_cancelar": self.url_cancelar or self.get_success_url(),
        })

    def post(self, request, *args, **kwargs):
        objeto = self.get_object()
        success_url = self.get_success_url()
        try:
            objeto.delete()
            messages.success(request, "Registro eliminado correctamente.")
        except (ProtectedError, RestrictedError):
            if hasattr(objeto, "estado"):
                objeto.estado = False
                objeto.save(update_fields=["estado"])
                messages.warning(
                    request,
                    "No se puede eliminar porque tiene registros asociados. Se desactivó el registro para proteger el historial."
                )
            else:
                messages.error(
                    request,
                    "No se puede eliminar porque tiene registros asociados. Puedes desactivarlo."
                )
        return redirect(success_url)
