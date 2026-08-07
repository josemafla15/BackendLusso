"""
FIX: agregar cache_control al último mensaje del historial, para que
Anthropic cachee TODO el prefijo (system + tools + conversación acumulada
hasta ese punto), no solo el system prompt.

Sin este cambio: cada turno paga precio completo por el historial creciente.
Con este cambio: el historial se sirve como cache_read (10% del precio)
en cada turno subsiguiente, dentro de la ventana de 5 minutos.
"""


def _marcar_ultimo_bloque_cacheable(messages):
    """
    Toma una lista de mensajes en formato Anthropic y le agrega
    cache_control al último bloque de contenido del último mensaje.
    Convierte content de string a lista de bloques si hace falta,
    porque cache_control solo se puede poner sobre un bloque, no
    sobre un string plano.
    """
    if not messages:
        return messages

    ultimo = messages[-1]
    contenido = ultimo["content"]

    if isinstance(contenido, str):
        ultimo["content"] = [
            {"type": "text", "text": contenido, "cache_control": {"type": "ephemeral"}}
        ]
    else:
        # ya es una lista de bloques (ej. tool_result) -> marcar el último bloque
        contenido[-1] = {**contenido[-1], "cache_control": {"type": "ephemeral"}}

    return messages


# --- Uso dentro de responder_mensaje() ---
#
# ANTES:
#
#     historial = _construir_historial(lead)
#     ...
#     messages = historial
#     for _ in range(5):
#         response = client.messages.create(
#             model=MODELO,
#             max_tokens=300,
#             system=[...],
#             tools=TOOLS,
#             messages=messages,
#         )
#         ...
#         messages = messages + [
#             {"role": "assistant", "content": response.content},
#             {"role": "user", "content": tool_results},
#         ]
#
# DESPUÉS (2 líneas nuevas, marcadas con >>>):
#
#     historial = _construir_historial(lead)
#     ...
#     messages = historial
#     for _ in range(5):
#         messages = _marcar_ultimo_bloque_cacheable(messages)          # >>> NUEVO
#         response = client.messages.create(
#             model=MODELO,
#             max_tokens=300,
#             system=[...],
#             tools=TOOLS,
#             messages=messages,
#         )
#         ...
#         messages = messages + [
#             {"role": "assistant", "content": response.content},
#             {"role": "user", "content": tool_results},
#         ]
#         # el siguiente loop del for vuelve a marcar el nuevo último mensaje
#
# Por qué SIEMPRE antes de cada client.messages.create(): porque el
# breakpoint tiene que estar en el ÚLTIMO mensaje que se envía en ESA
# llamada específica. Si el bucle de tool use agrega un tool_result,
# ese tool_result se vuelve el nuevo "último mensaje" en la siguiente
# vuelta, y hay que volver a marcarlo ahí (el marcador de la llamada
# anterior deja de ser el último bloque, pero no rompe nada -- solo
# ya no es el punto de corte activo).


def log_uso_cache(logger, lead_id, response):
    """
    Llamar esto justo después de cada client.messages.create().
    Te dice, con datos reales (no estimados), si el caching está
    funcionando en esa llamada específica.
    """
    u = response.usage
    logger.info(
        "CACHE lead=%s | input_nuevo=%d | cache_write=%d | cache_read=%d | output=%d",
        lead_id, u.input_tokens, u.cache_creation_input_tokens,
        u.cache_read_input_tokens, u.output_tokens,
    )

    # Diagnóstico automático de qué está pasando:
    if u.cache_creation_input_tokens == 0 and u.cache_read_input_tokens == 0:
        logger.warning(
            "CACHE lead=%s: NO se está aplicando caching en esta llamada "
            "(ambos contadores en 0). Revisa que cache_control esté "
            "presente en el bloque correcto.", lead_id
        )
    elif u.cache_read_input_tokens > 0:
        logger.info(
            "CACHE lead=%s: HIT -- %d tokens servidos desde cache (10%% del "
            "precio) en vez de precio completo.", lead_id, u.cache_read_input_tokens
        )
    elif u.cache_creation_input_tokens > 0:
        logger.info(
            "CACHE lead=%s: WRITE -- primera vez que se ve este prefijo, o "
            "el cache anterior expiró (>5 min sin uso). Se paga 1.25x esta "
            "vez, pero el siguiente turno (si llega en <5 min) debería dar HIT.",
            lead_id
        )

    # Costo real de ESTA llamada específica con precios oficiales Haiku 4.5
    costo = (
        u.input_tokens * 1.00 / 1_000_000
        + u.cache_creation_input_tokens * 1.25 / 1_000_000
        + u.cache_read_input_tokens * 0.10 / 1_000_000
        + u.output_tokens * 5.00 / 1_000_000
    )
    logger.info("CACHE lead=%s: costo de esta llamada = $%.6f", lead_id, costo)
    return costo


# --- Uso dentro de responder_mensaje(), junto con el fix anterior ---
#
#     for _ in range(5):
#         messages = _marcar_ultimo_bloque_cacheable(messages)
#         response = client.messages.create(
#             model=MODELO,
#             max_tokens=300,
#             system=[...],
#             tools=TOOLS,
#             messages=messages,
#         )
#         log_uso_cache(logger, lead_id, response)          # >>> NUEVO
#         ...