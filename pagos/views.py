from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Pago
from .wompi_service import datos_widget


@require_GET
def resolver_pago(request, token):
    """Endpoint PÚBLICO (sin auth) — el cliente lo consulta desde /pago/{token}."""
    try:
        pago = Pago.objects.get(token=token)
    except Pago.DoesNotExist:
        return JsonResponse({"error": "Link no válido"}, status=404)

    if pago.estado != Pago.Estado.PENDIENTE:
        return JsonResponse({
            "error": "Este pago ya fue procesado o no está disponible",
            "estado": pago.estado,
        }, status=410)

    return JsonResponse({
        "cliente_nombre": pago.cliente_nombre,
        "destino": pago.destino,
        "descripcion": pago.descripcion,
        "monto": str(pago.monto),
        "widget": datos_widget(pago),
    })