from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.inicio, name="inicio"),

    # Almacenes
    path("almacenes/", views.AlmacenListView.as_view(), name="almacen_listado"),
    path("almacenes/nuevo/", views.AlmacenCreateView.as_view(), name="almacen_crear"),
    path("almacenes/<int:pk>/editar/", views.AlmacenUpdateView.as_view(), name="almacen_editar"),
    path("almacenes/<int:pk>/eliminar/", views.AlmacenDeleteView.as_view(), name="almacen_eliminar"),
]
