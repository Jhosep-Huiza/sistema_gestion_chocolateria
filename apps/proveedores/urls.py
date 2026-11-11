from django.urls import path
from . import views
urlpatterns = [
    path("", views.listado, name="proveedores_listado"),
    path("nuevo/", views.crear, name="proveedores_crear"),
    path("<int:pk>/editar/", views.editar, name="proveedores_editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="proveedores_eliminar"),
]
