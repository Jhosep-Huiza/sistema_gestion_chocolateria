from django.urls import path
from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("<slug:clave>/exportar/<str:formato>/", views.exportar, name="exportar"),
    path("<slug:clave>/", views.reporte, name="reporte"),
]
