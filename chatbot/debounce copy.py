import os
import uuid

import redis

logger_redis = None
_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )
    return _redis_client


def registrar_evento(lead_id, ttl_seconds=120):
    """Genera un token nuevo para este lead y lo marca como 'el evento más
    reciente'. Devuelve el token que la tarea deberá verificar antes de
    procesar — si para cuando le toque ejecutarse ya no es el más reciente,
    debe abortar (llegó un mensaje más nuevo que se encargará de todo)."""
    token = uuid.uuid4().hex
    _get_redis().set(f"debounce:lead:{lead_id}", token, ex=ttl_seconds)
    return token


def es_evento_vigente(lead_id, token):
    """True si `token` sigue siendo el más reciente registrado para este lead."""
    actual = _get_redis().get(f"debounce:lead:{lead_id}")
    return actual is not None and actual.decode() == token