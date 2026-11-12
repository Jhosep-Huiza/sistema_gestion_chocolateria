app_name = "finanzas"
from django.urls import path
from . import views
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("gastos/", views.gastos, name="gastos"),
    path("gastos/nuevo/", views.crear_gasto, name="gasto_crear"),
    path("gastos/<int:pk>/editar/", views.editar_gasto, name="gasto_editar"),
    path("gastos/<int:pk>/anular/", views.anular, name="gasto_anular"),
]
