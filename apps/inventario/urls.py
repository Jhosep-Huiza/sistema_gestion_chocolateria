from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("stock/", views.StockListView.as_view(), name="stock"),
    path("lotes/", views.LoteListView.as_view(), name="lotes"),
    path("lotes/<int:pk>/estado/", views.actualizar_estado_lote, name="lote_estado"),
    path("lotes/<int:pk>/", views.lote_detalle, name="lote_detalle"),
    path("kardex/", views.MovimientoListView.as_view(), name="movimientos"),
    path("ajustes/nuevo/", views.nuevo_ajuste, name="ajustar"),
    path("transferencias/nueva/", views.nueva_transferencia, name="transferir"),

    # Almacenes
    path("almacenes/", views.AlmacenListView.as_view(), name="almacen_listado"),
    path("almacenes/nuevo/", views.AlmacenCreateView.as_view(), name="almacen_crear"),
    path("almacenes/<int:pk>/editar/", views.AlmacenUpdateView.as_view(), name="almacen_editar"),
    path("almacenes/<int:pk>/eliminar/", views.AlmacenDeleteView.as_view(), name="almacen_eliminar"),
]
