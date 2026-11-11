from django.urls import path
from . import views

app_name = "configuracion"

urlpatterns = [
    # Configuración de empresa / negocio
    path("", views.ConfiguracionNegocioView.as_view(), name="inicio"),

    # Métodos de Pago
    path("metodos-pago/", views.MetodoPagoListView.as_view(), name="metodo_pago_listado"),
    path("metodos-pago/nuevo/", views.MetodoPagoCreateView.as_view(), name="metodo_pago_crear"),
    path("metodos-pago/<int:pk>/editar/", views.MetodoPagoUpdateView.as_view(), name="metodo_pago_editar"),
    path("metodos-pago/<int:pk>/eliminar/", views.MetodoPagoDeleteView.as_view(), name="metodo_pago_eliminar"),
]
