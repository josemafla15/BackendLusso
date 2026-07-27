import json
import logging
import os

from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from leads.models import Lead

from .debounce import registrar_evento
from .models import Mensaje

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook_meta(request):
    """Punto de entrada del webhook de WhatsApp (Meta Cloud API)."""
    if request.method == "GET":
        return _verificar(request)
    return _recibir(request)


def _verificar(request):
    """Handshake de verificación: Meta manda un reto y hay que devolverlo."""
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == os.environ["WHATSAPP_VERIFY_TOKEN"]:
        return HttpResponse(challenge)
    return HttpResponse("Verificación fallida", status=403)


def _recibir(request):
    """Procesa los eventos POST: guarda mensajes entrantes como Mensaje."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                _procesar_valor(value)
    except Exception:
        # Nunca devolvemos error a Meta: registramos y respondemos 200
        # para evitar reintentos infinitos. El log nos cuenta qué pasó.
        logger.exception("Error procesando webhook de Meta")

    return HttpResponse(status=200)


def _procesar_valor(value):
    """Extrae mensajes de un bloque 'value' del payload de Meta."""
    mensajes = value.get("messages")
    if not mensajes:
        return

    contactos = value.get("contacts", [])
    nombre_wa = ""
    if contactos:
        nombre_wa = contactos[0].get("profile", {}).get("name", "")

    for msg in mensajes:
        telefono = msg.get("from")
        wa_message_id = msg.get("id")
        tipo = msg.get("type")

        if tipo == "text":
            contenido = msg.get("text", {}).get("body", "")
        else:
            contenido = f"[{tipo} recibido — no soportado aún]"

        lead = _obtener_o_crear_lead(telefono, nombre_wa)

        try:
            Mensaje.objects.create(
                lead=lead,
                rol=Mensaje.Rol.CLIENTE,
                contenido=contenido,
                wa_message_id=wa_message_id,
            )
        except IntegrityError:
            logger.info("Mensaje duplicado ignorado: %s", wa_message_id)
            continue

        logger.info("Mensaje guardado de %s: %s", telefono, contenido[:50])

        # ¿Responde el bot? — interruptor manual + pausa con vencimiento
        pausado = lead.bot_pausado_hasta and lead.bot_pausado_hasta > timezone.now()
        if lead.bot_activo and not pausado:
            from .whatsapp import marcar_leido_y_escribiendo
            marcar_leido_y_escribiendo(wa_message_id)

            # Debounce: registramos este evento como "el más reciente" y
            # encolamos con una espera de 5s. Si llega otro mensaje antes de
            # que se cumpla, esta tarea se auto-descartará al ejecutarse.
            from .tasks import procesar_mensaje_entrante
            token = registrar_evento(str(lead.id))
            procesar_mensaje_entrante.apply_async(
                args=[str(lead.id), token], countdown=5,
            )
        else:
            logger.info("Bot inactivo/pausado para %s — solo se guardó", lead.nombre)
            # TODO: notificación de actividad-en-pausa al asesor (con anti-ruido)


def _obtener_o_crear_lead(telefono, nombre_wa):
    """Upsert del lead de WhatsApp por teléfono."""
    lead, creado = Lead.objects.get_or_create(
        telefono=telefono,
        origen=Lead.Origen.WHATSAPP,
        defaults={
            "nombre": nombre_wa or telefono,
            "contacto": telefono,
            "estado": Lead.Estado.EN_CONVERSACION,
        },
    )
    if creado:
        logger.info("Lead nuevo de WhatsApp: %s (%s)", lead.nombre, telefono)
    return lead