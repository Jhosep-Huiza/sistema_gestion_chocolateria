app_name = "devoluciones"
from django.urls import path
from . import views
urlpatterns = [
    path("", views.inicio, name="listado"),
    path("", views.inicio, name="inicio"),
    path("nueva/", views.crear, name="crear"),
    path("<int:pk>/aprobar/", views.aprobar, name="aprobar"),
    path("<int:pk>/rechazar/", views.rechazar, name="rechazar"),
]
