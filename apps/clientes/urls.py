from django.urls import path
from . import views
urlpatterns = [
    path("", views.listado, name="clientes_listado"),
    path("nuevo/", views.crear, name="clientes_crear"),
    path("<int:pk>/editar/", views.editar, name="clientes_editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="clientes_eliminar"),
]
