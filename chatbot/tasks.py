import logging

from celery import shared_task

from .debounce import es_evento_vigente

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def procesar_mensaje_entrante(self, lead_id, token=None):
    # Debounce: si llegó un mensaje más nuevo mientras esperábamos, esta
    # tarea quedó obsoleta — la tarea del mensaje nuevo se encargará de todo.
    if token and not es_evento_vigente(lead_id, token):
        logger.info(
            "Tarea obsoleta para lead %s — se descarta (llegó mensaje más nuevo)",
            lead_id,
        )
        return

    from .claude_service import responder_mensaje

    try:
        responder_mensaje(lead_id)
    except Exception as exc:
        logger.exception("Error procesando mensaje del lead %s", lead_id)
        raise self.retry(exc=exc)