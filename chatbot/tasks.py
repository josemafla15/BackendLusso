import logging

from celery import shared_task

from .debounce import es_evento_vigente, hay_evento_mas_nuevo

logger = logging.getLogger(__name__)

# Si la API de Anthropic sigue caída tras los reintentos inmediatos del SDK,
# se vuelve a intentar a los 1, 2 y 3 minutos.
REINTENTOS_API = 3


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def procesar_mensaje_entrante(self, lead_id, token=None):
    es_reintento = self.request.retries > 0

    # Debounce: si llegó un mensaje más nuevo mientras esperábamos, esta
    # tarea quedó obsoleta — la tarea del mensaje nuevo se encargará de todo.
    # En un reintento el token puede haber expirado (dura 120 s) sin que eso
    # signifique que llegó otro mensaje, así que solo se descarta si de
    # verdad hay un token distinto.
    if token:
        obsoleta = (
            hay_evento_mas_nuevo(lead_id, token) if es_reintento
            else not es_evento_vigente(lead_id, token)
        )
        if obsoleta:
            logger.info(
                "Tarea obsoleta para lead %s — se descarta (llegó mensaje más nuevo)",
                lead_id,
            )
            return

    from .claude_service import FalloAPI, responder_mensaje

    try:
        responder_mensaje(lead_id, avisar_fallo=not es_reintento)
    except FalloAPI as exc:
        if self.request.retries >= REINTENTOS_API:
            logger.error(
                "Lead %s: la IA no respondió tras %d reintentos — el cliente quedó sin respuesta",
                lead_id, REINTENTOS_API,
            )
            _avisar_en_portal(lead_id)
            return
        raise self.retry(
            exc=exc,
            countdown=60 * (self.request.retries + 1),
            max_retries=REINTENTOS_API,
        )
    except Exception as exc:
        logger.exception("Error procesando mensaje del lead %s", lead_id)
        raise self.retry(exc=exc)


def _avisar_en_portal(lead_id):
    """Deja constancia en el chat del lead para que el asesor lo atienda."""
    try:
        from leads.models import Lead

        from .models import Mensaje

        Mensaje.objects.create(
            lead=Lead.objects.get(id=lead_id), rol=Mensaje.Rol.SISTEMA,
            contenido="⚠️ La IA no pudo responder a este cliente. Atender manualmente.",
        )
    except Exception:
        logger.exception("No se pudo dejar el aviso en el portal para el lead %s", lead_id)