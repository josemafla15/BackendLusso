from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Cotizacion

BLOQUES_DISPONIBLES = {
    "portada": "cotizaciones/bloques/cotizacion_portada.html",
    "organizamos": "cotizaciones/bloques/cotizacion_organizamos.html",
    "despertar": "cotizaciones/bloques/cotizacion_despertar.html",
    "bienvenidos": "cotizaciones/bloques/cotizacion_bienvenidos.html",
    "viajesonado": "cotizaciones/bloques/cotizacion_viajesonado.html",
    "artevivir": "cotizaciones/bloques/cotizacion_artevivir.html",
    "hotel": "cotizaciones/bloques/cotizacion_hotel.html",
    "vuelos": "cotizaciones/bloques/cotizacion_vuelos.html",
    "experiencia": "cotizaciones/bloques/cotizacion_experiencia.html",
    "inversion": "cotizaciones/bloques/cotizacion_inversion.html",
    "creamos": "cotizaciones/bloques/cotizacion_creamos.html",
    "sobrenosotros": "cotizaciones/bloques/cotizacion_sobrenosotros.html",
    "recuerdo": "cotizaciones/bloques/cotizacion_recuerdo.html",
    "buenviaje": "cotizaciones/bloques/cotizacion_buenviaje.html",
    "completa": "cotizaciones/bloques/cotizacion_completa.html",
}


def preview_bloque(request, cotizacion_id, bloque):
    template = BLOQUES_DISPONIBLES.get(bloque)
    if template is None:
        raise Http404(f"Bloque '{bloque}' no existe. Opciones: {list(BLOQUES_DISPONIBLES)}")

    cotizacion = get_object_or_404(Cotizacion, id=cotizacion_id)
    return render(request, template, {"cotizacion": cotizacion})