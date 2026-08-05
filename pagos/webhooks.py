import hashlib
import hmac
import json
import logging
import os

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Pago

logger = logging.getLogger(__name__)

ESTADO_MAP = {
    "PENDING": Pago.Estado.PENDIENTE,
    "APPROVED": Pago.Estado.APROBADO,
    "DECLINED": Pago.Estado.DECLINADO,
    "VOIDED": Pago.Estado.ANULADO,  # cancelado O reembolsado — Wompi no distingue
    "ERROR": Pago.Estado.ERROR,
}


def _validar_checksum(payload):
    """Algoritmo oficial de Wompi para eventos:
    SHA256(valores de signature.properties, en el orden dado + timestamp + WOMPI_EVENTS_SECRET)
    Las 'properties' las manda Wompi dinámicamente en cada evento — no se hardcodean."""
    signature = payload.get("signature", {})
    properties = signature.get("properties", [])
    checksum_recibido = signature.get("checksum", "")
    timestamp = payload.get("timestamp", "")
    data = payload.get("data", {})

    cadena = ""
    for prop_path in properties:
        valor = data
        for parte in prop_path.split("."):  # SIN el [1:] — recorre TODO el path completo
            valor = valor.get(parte) if isinstance(valor, dict) else None
        cadena += str(valor) if valor is not None else ""

    cadena += str(timestamp)
    cadena += os.environ["WOMPI_EVENTS_SECRET"]

    checksum_calculado = hashlib.sha256(cadena.encode()).hexdigest()
    return hmac.compare_digest(checksum_calculado, checksum_recibido)

@csrf_exempt
@require_POST
def webhook_wompi(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if not _validar_checksum(payload):
        logger.warning("Webhook de Wompi con firma inválida — posible intento de falsificación")
        return HttpResponse(status=403)

    if payload.get("event") != "transaction.updated":
        return HttpResponse(status=200)  # otros tipos de evento, no aplican aún

    tx = payload.get("data", {}).get("transaction", {})
    wompi_id = tx.get("id")
    referencia = tx.get("reference")
    status_wompi = tx.get("status")

    try:
        pago = Pago.objects.get(referencia=referencia)
    except Pago.DoesNotExist:
        logger.error("Webhook de Wompi con referencia desconocida: %s", referencia)
        return HttpResponse(status=200)  # 200 igual: Wompi no debe reintentar por esto

    nuevo_estado = ESTADO_MAP.get(status_wompi, Pago.Estado.ERROR)

    # Idempotencia: si ya procesamos exactamente este evento, no hacer nada de nuevo
    if pago.wompi_transaction_id == wompi_id and pago.estado == nuevo_estado:
        logger.info("Webhook duplicado ignorado para %s", referencia)
        return HttpResponse(status=200)

    pago.wompi_transaction_id = wompi_id
    pago.estado = nuevo_estado
    pago.metodo_pago = tx.get("payment_method_type")
    pago.webhook_payload = payload
    pago.save(update_fields=[
        "wompi_transaction_id", "estado", "metodo_pago", "webhook_payload", "updated_at",
    ])

    logger.info("Pago %s -> %s (Wompi tx %s)", pago.referencia, pago.estado, wompi_id)
    return HttpResponse(status=200)