from django.urls import path
from . import views
urlpatterns = [
    path("", views.listado, name="productos_listado"),
    path("nuevo/", views.crear, name="productos_crear"),
    path("<int:pk>/editar/", views.editar, name="productos_editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="productos_eliminar"),
]
