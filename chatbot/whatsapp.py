import logging
import os

import requests

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v25.0"


def enviar_texto(telefono, texto):
    """Envía un mensaje de texto libre por WhatsApp (ventana de servicio)."""
    url = f"{GRAPH_URL}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    headers = {
        "Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        logger.error("Error enviando WhatsApp a %s: %s", telefono, resp.text)
    resp.raise_for_status()
    return resp.json()


def enviar_plantilla(telefono, nombre_plantilla, parametros, idioma="es"):
    """
    Envía un mensaje usando una PLANTILLA aprobada por Meta -- necesario
    para iniciar conversaciones fuera de la ventana de 24h de servicio
    (ej. notificar al asesor, que nunca le escribió primero al bot).

    telefono:         número de destino (con código de país, solo dígitos)
    nombre_plantilla: nombre exacto de la plantilla, tal como quedó
                       aprobada en Meta Business Manager
    parametros:       lista de strings, en el mismo orden que los
                       placeholders {{1}}, {{2}}, etc. de la plantilla
    idioma:           código de idioma de la plantilla (default "es")
    """
    url = f"{GRAPH_URL}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    headers = {
        "Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": nombre_plantilla,
            "language": {"code": idioma},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in parametros],
                }
            ],
        },
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        logger.error("Error enviando plantilla WhatsApp a %s: %s", telefono, resp.text)
    resp.raise_for_status()
    return resp.json()


def marcar_leido_y_escribiendo(wa_message_id):
    """Marca el mensaje como leído y muestra el indicador de escritura."""
    url = f"{GRAPH_URL}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    headers = {
        "Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": wa_message_id,
        "typing_indicator": {"type": "text"},
    }
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception:
        logger.warning("No se pudo enviar typing indicator", exc_info=True)