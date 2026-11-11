from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.usuarios import views as auth_views
from apps.reportes.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("", dashboard, name="dashboard"),
    path("clientes/", include("apps.clientes.urls")),
    path("productos/", include("apps.productos.urls")),
    path("proveedores/", include("apps.proveedores.urls")),
    path("compras/", include("apps.compras.urls")),
    path("inventario/", include("apps.inventario.urls")),
    path("ventas/", include("apps.ventas.urls")),
    path("devoluciones/", include("apps.devoluciones.urls")),
    path("caja/", include("apps.caja.urls")),
    path("finanzas/", include("apps.finanzas.urls")),
    path("reportes/", include("apps.reportes.urls")),
    path("configuracion/", include("apps.configuracion.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
