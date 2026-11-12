app_name = "ventas"
from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("historial/", views.VentaListView.as_view(), name="historial"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/comprobante/", views.comprobante, name="comprobante"),
    path("<int:pk>/pagos/nuevo/", views.registrar_pago, name="pago"),
    path("<int:pk>/anular/", views.anular, name="anular"),
]
