app_name = "caja"
from django.urls import path
from . import views
urlpatterns = [path("", views.inicio, name="inicio")]
