app_name = "caja"
from django.urls import path
from . import views
urlpatterns = [path("", views.inicio, name="inicio")]
urlpatterns += [
    path("<int:pk>/movimiento/", views.movimiento, name="movimiento"),
    path("<int:pk>/cerrar/", views.cerrar, name="cerrar"),
    path("<int:pk>/resumen/", views.resumen, name="resumen"),
]
