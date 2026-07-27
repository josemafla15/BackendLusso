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