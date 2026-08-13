from django.urls import path
from .views import buscar_destino_contenido
from . import views

app_name = "cotizaciones"

urlpatterns = [
    path(
        "preview/<uuid:cotizacion_id>/<str:bloque>/",
        views.preview_bloque,
        name="preview_bloque",
    ),
    path("admin/cotizaciones/buscar-destino/", buscar_destino_contenido, name="buscar_destino_contenido"),
]