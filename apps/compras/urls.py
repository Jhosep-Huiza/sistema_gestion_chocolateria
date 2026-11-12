app_name = "compras"
from django.urls import path
from . import views

app_name = "compras"

urlpatterns = [
    path("", views.CompraListView.as_view(), name="listado"),
    path("nueva/", views.crear, name="crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/recepcion/", views.recepcion, name="recepcion"),
    path("<int:pk>/pagos/nuevo/", views.registrar_pago, name="pago"),
    path("<int:pk>/anular/", views.anular, name="anular"),
]
