from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path("perfil/", views.MiPerfilView.as_view(), name="perfil"),
    path("", views.UsuarioListView.as_view(), name="listado"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.UsuarioDeleteView.as_view(), name="eliminar"),
    path("<int:pk>/estado/", views.UsuarioEstadoView.as_view(), name="estado"),
]
