from django.urls import path

from . import views

app_name = "cotizaciones"

urlpatterns = [
    path(
        "preview/<uuid:cotizacion_id>/<str:bloque>/",
        views.preview_bloque,
        name="preview_bloque",
    ),
]