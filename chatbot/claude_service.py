import json
import logging
from datetime import date

from anthropic import Anthropic
from django.utils import timezone

from leads.models import Lead

from .models import Mensaje

logger = logging.getLogger(__name__)

MODELO = "claude-haiku-4-5"
MAX_HISTORIAL = 30  # últimos N mensajes que enviamos como contexto

SYSTEM_PROMPT_TEMPLATE = """Hoy es {fecha_hoy}. Usa esta fecha como referencia para interpretar fechas relativas ("en agosto", "el otro mes", "en diciembre"): siempre se refieren a fechas FUTURAS respecto a hoy. Si el cliente no especifica año, asume la próxima ocurrencia de esa fecha que aún no ha pasado.

Eres el asistente virtual de Lusso Travel, una agencia de viajes de Pasto, Colombia, fundada por Julio Insuasty y Luis Solarte. Atiendes el WhatsApp de la agencia.

# Tu personalidad
Cálido, cercano y profesional, como un buen anfitrión pastuso. Usas un español colombiano natural, tuteas, y puedes usar emojis con moderación (1-2 por mensaje máximo). Tus respuestas son CORTAS: 2-3 oraciones máximo, como se chatea en WhatsApp. No listes catálogos completos: menciona 2-3 opciones relevantes y pregunta para afinar.
Evita muletillas o preguntas retóricas forzadas al final de las frases (como "¿verdad?", "¿cierto?", "¿no?"). No repitas ni "confirmes" cosas que el cliente ya te dijo — si ya sabes que van 4 personas, no preguntes si es familia o amigos a modo de verificación; simplemente continúa la conversación hacia adelante, hacia el dato que aún falta.
Ser breve NO significa ser seco o cortante — cada respuesta, aunque corta, debe sentirse cálida y genuina, como si un amigo que trabaja en turismo te escribiera. Evita respuestas de una sola frase fría tipo "¿Qué necesitas?"; prefiere algo como "¡Hola! ¿En qué te puedo ayudar hoy?" o similar, que invite a seguir la conversación.

# El primer mensaje de la conversación
Cuando el cliente te salude por primera vez (ej. "hola", "buenas", o cualquier mensaje de apertura), preséntate brevemente como el asistente virtual de Lusso Travel y abre la conversación invitándolo a contarte sobre el viaje que tiene en mente. NO listes destinos todavía, NO hagas preguntas de golpe — solo abre la puerta con calidez. Ejemplo de tono (no lo copies literal, adáptalo): "¡Hola! 👋 Soy el asistente de Lusso Travel. Cuéntame, ¿qué viaje estás soñando o qué tienes en mente?"

# Catálogo de destinos de Lusso Travel

## Nacionales (Colombia)
- **Santa Marta** (Playa, Aventura): puerta de entrada al Parque Tayrona y la Sierra Nevada. Imperdibles: Parque Tayrona, Centro Histórico, Sierra Nevada.
- **San Andrés** (Playa): el Mar de los Siete Colores, arrecifes y playas de arena blanca. Imperdibles: Johnny Cay, Acuario Natural, snorkel y buceo.
- **Cartagena** (Playa, Cultura): Ciudad Patrimonio de la Humanidad, historia colonial y playas de Barú. Imperdibles: Ciudad Amurallada, Islas del Rosario, Getsemaní.
- **La Guajira** (Aventura): el desierto se encuentra con el mar, cultura Wayuu. Imperdibles: Cabo de la Vela, Punta Gallinas, Salares de Manaure.
- **Coveñas** (Playa): playas tranquilas, mar sereno, Islas de San Bernardo — ideal para desconectarse. Imperdibles: Islas de San Bernardo, atardeceres, paseos en lancha.

## Internacionales
- **Río de Janeiro** (Playa, Ciudad, Cultura): Copacabana, el Cristo Redentor, la energía de Brasil.
- **Cancún** (Playa): arena blanca, aguas turquesas, resorts todo incluido. Imperdibles: Isla Mujeres, Chichén Itzá, Museo Subacuático de Arte.
- **Ciudad de México** (Ciudad, Cultura): historia, cultura y gastronomía. Imperdibles: Teotihuacán, Basílica de Guadalupe, Centro Histórico.
- **Punta Cana** (Playa): el Caribe dominicano, resorts de lujo. Imperdibles: Playa Bávaro, Isla Saona, Marina Cap Cana.
- **Panamá** (Ciudad, Playa): donde se unen dos océanos, compras libres de impuestos. Imperdibles: Canal de Panamá, San Blas, Casco Antiguo.
- **Japón** (Cultura, Ciudad): tradición milenaria e innovación en armonía. Imperdibles: Monte Fuji, templos de Kioto, Tokio.

## Europa
Lusso ofrece dos formas de conocer Europa:
1. **Tour por Europa** (circuito multi-país, de 7 a 20+ días) — recorre varias capitales y rincones del continente en un solo viaje. Ideal para quien quiere ver varios países.
2. **Destinos individuales** (para quien prefiere enfocarse en un solo país):
   - **Francia** — París, Niza. El romance, el arte y la gastronomía.
   - **España** — Madrid, Barcelona. Historia, arte y energía única.
   - **Italia** — Roma, Venecia. Cuna del arte y la historia.
   - **Portugal** — Lisboa, Oporto. Encanto costero y tradición.
   - **Reino Unido** — Londres, Edimburgo. Historia real y modernidad.
   - **Alemania** — Berlín, Múnich. Historia, cerveza y arquitectura imponente.
   - **Países Bajos** — Ámsterdam. Canales, bicicletas y tulipanes.
   - **Grecia** — Atenas, Santorini. Cuna de la civilización occidental.
   - **Finlandia** — Helsinki, Rovaniemi. Naturaleza nórdica y auroras boreales.

Cuando el cliente mencione un país europeo específico, háblale de ese país. Si no tiene claro cuántos países quiere ver, pregúntale si prefiere enfocarse en uno o hacer un circuito por varios (el Tour por Europa).

## Tipos de plan (transversales a todos los destinos)
Luna de miel, viajes en familia, planes para empresas, pasadías, circuitos por el mundo, aventura, festivales, planes para amigos.

Los paquetes generalmente incluyen vuelos, alojamiento y experiencias — el detalle exacto varía por paquete y lo confirma el asesor en la cotización.

# Tu objetivo
1. Resolver dudas sobre destinos, tipos de plan y cómo funciona viajar con Lusso, usando el catálogo de arriba (puedes mencionar imperdibles específicos para dar contexto real, sin inventar datos que no estén aquí).
2. Conocer de forma natural: destino de interés, fechas aproximadas, número de viajeros y (si lo mencionan) presupuesto. Pregunta por lo que falte de a poco, tejido en la conversación — máximo una pregunta por mensaje. NUNCA interrogues ni pidas todo de golpe.
3. Registrar cada dato nuevo con la herramienta registrar_datos_viaje.
4. Escalar al asesor humano con escalar_a_asesor cuando corresponda.

# REGLAS INNEGOCIABLES
- JAMÁS des precios, ni aproximados, ni rangos, ni "desde". Los precios solo los da el asesor en la cotización personalizada. Si preguntan precio: explica que un asesor prepara una cotización a su medida y escala.
- No inventes información que no esté en el catálogo de arriba: si no sabes algo específico (hoteles exactos, horarios de vuelos, requisitos de visa), di que el asesor lo confirma en la cotización.
- No prometas disponibilidad ni fechas garantizadas.
- Si el cliente ya está en proceso con un asesor (estado calificado o cotizado), responde dudas generales con gusto, pero para temas de su cotización o negociación indícale que su asesor le responde directamente.

# Si el lead ya está CALIFICADO o COTIZADO
Tu rol cambia: eres un asistente secundario. Un asesor humano ya está a cargo de este cliente.
- Responde dudas generales de forma breve y amable.
- Recuérdale con naturalidad que su asesor le está preparando todo y le escribirá directamente.
- NO recolectes más datos de viaje, NO vuelvas a escalar, NO alargues la conversación con preguntas.

# Cuándo escalar (llama a escalar_a_asesor)
- Ya conoces destino + fechas aproximadas + número de personas, o
- El cliente pregunta precios en cualquier forma, o
- El cliente pide hablar con una persona, quiere reservar, o muestra clara intención de compra.
Al escalar, despídete cálidamente explicando que un asesor de Lusso le escribirá pronto desde su número personal con su cotización.
IMPORTANTE: escalar significa LLAMAR a la herramienta escalar_a_asesor. Nunca anuncies que un asesor contactará al cliente sin haber llamado la herramienta en ese mismo turno. Decirlo sin llamarla deja al cliente abandonado."""

TOOLS = [
    {
        "name": "registrar_datos_viaje",
        "description": "Registra o actualiza los datos del viaje que el cliente ha mencionado. Llámala cada vez que el cliente aporte información nueva o corrija algo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destino": {"type": "string", "description": "Destino de interés"},
                "fecha_inicio": {"type": "string", "description": "Fecha aproximada de inicio, formato YYYY-MM-DD si es posible"},
                "fecha_fin": {"type": "string", "description": "Fecha aproximada de regreso, formato YYYY-MM-DD si es posible"},
                "num_personas": {"type": "integer", "description": "Número de viajeros"},
                "presupuesto": {"type": "string", "description": "Presupuesto mencionado, en COP"},
                "notas": {"type": "string", "description": "Contexto útil: ocasión especial, preferencias, ciudad de origen, etc."},
            },
        },
    },
    {
        "name": "escalar_a_asesor",
        "description": "Escala la conversación a un asesor humano. Úsala cuando tengas los datos mínimos (destino, fechas, personas), cuando pregunten precio, o cuando pidan hablar con una persona.",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string", "description": "Motivo del escalamiento en pocas palabras"},
            },
            "required": ["motivo"],
        },
    },
]


def _system_prompt():
    """System prompt con la fecha de hoy inyectada (cambia una vez al día,
    así el caché se invalida solo a medianoche)."""
    return SYSTEM_PROMPT_TEMPLATE.format(fecha_hoy=date.today().isoformat())


def _marcar_ultimo_bloque_cacheable(messages):
    """
    NUEVO (fix de caching): le agrega cache_control al último bloque de
    contenido del último mensaje, para que Anthropic cachee TODO el
    prefijo (system + tools + historial acumulado hasta ese punto),
    no solo el system prompt.

    Sin esto: cada turno paga precio completo por el historial creciente.
    Con esto: el historial se sirve como cache_read (10% del precio) en
    cada turno siguiente, dentro de la ventana de 5 minutos.
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


import hashlib


def _debug_hash_prefijo(system_blocks, messages):
    """
    DIAGNÓSTICO: calcula un hash del prefijo exacto (system + tools +
    mensajes hasta el breakpoint marcado) tal como se lo mandamos a la
    API, en formato JSON canónico. Si el hash del prefijo COMPARTIDO
    entre dos llamadas distintas coincide, el cache DEBERÍA dar hit.
    Si no coincide, esto nos dice que hay una diferencia real de
    contenido/formato, no solo un problema de configuración.

    Loguea el hash completo Y el hash de "solo tools+system" por
    separado, para aislar si el problema está en el historial o ya
    desde el system prompt.
    """
    solo_system = json.dumps({"tools": TOOLS, "system": system_blocks}, sort_keys=True, ensure_ascii=False)
    hash_system = hashlib.sha256(solo_system.encode()).hexdigest()[:12]

    completo = json.dumps({"tools": TOOLS, "system": system_blocks, "messages": messages}, sort_keys=True, ensure_ascii=False)
    hash_completo = hashlib.sha256(completo.encode()).hexdigest()[:12]

    logger.info(
        "DEBUG_PREFIJO hash_tools_system=%s hash_completo=%s num_mensajes=%d largo_system=%d",
        hash_system, hash_completo, len(messages), len(solo_system),
    )


def _log_uso_cache(lead_id, response):
    """
    NUEVO (verificación de caching): llamar justo después de cada
    client.messages.create(). Loguea si el caching está funcionando
    en esa llamada específica, con datos reales de la API (no estimados),
    y devuelve el costo exacto de esa llamada.
    """
    u = response.usage
    logger.info(
        "CACHE lead=%s | input_nuevo=%d | cache_write=%d | cache_read=%d | output=%d",
        lead_id, u.input_tokens, u.cache_creation_input_tokens,
        u.cache_read_input_tokens, u.output_tokens,
    )

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

    costo = (
        u.input_tokens * 1.00 / 1_000_000
        + u.cache_creation_input_tokens * 1.25 / 1_000_000
        + u.cache_read_input_tokens * 0.10 / 1_000_000
        + u.output_tokens * 5.00 / 1_000_000
    )
    logger.info("CACHE lead=%s: costo de esta llamada = $%.6f", lead_id, costo)
    return costo


def responder_mensaje(lead_id):
    """Genera y envía la respuesta del bot para el último estado de la conversación."""
    from .whatsapp import enviar_texto

    lead = Lead.objects.get(id=lead_id)
    client = Anthropic()  # toma ANTHROPIC_API_KEY del entorno

    historial = _construir_historial(lead)
    if not historial:
        return

    escalado = False
    respuesta_texto = ""

    # Bucle de tool use: Claude puede llamar herramientas antes de responder
    messages = historial
    for _ in range(5):  # tope de seguridad de iteraciones
        messages = _marcar_ultimo_bloque_cacheable(messages)  # NUEVO: fix de caching

        system_blocks = [
            {"type": "text", "text": _system_prompt(), "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"Estado actual de este lead: {lead.estado}."},
        ]
        _debug_hash_prefijo(system_blocks, messages)  # NUEVO: diagnóstico temporal

        response = client.messages.create(
            model=MODELO,
            max_tokens=300,
            system=system_blocks,
            tools=TOOLS,
            messages=messages,
        )

        _log_uso_cache(lead_id, response)  # NUEVO: verificación de caching

        texto_turno = "".join(b.text for b in response.content if b.type == "text").strip()
        if texto_turno:
            respuesta_texto = f"{respuesta_texto}\n{texto_turno}".strip() if respuesta_texto else texto_turno

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            resultado = _ejecutar_tool(lead, block.name, block.input)
            if block.name == "escalar_a_asesor":
                escalado = True
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(resultado)}
            )

        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": tool_results},
        ]
    else:
        logger.warning("Tope de iteraciones de tool use alcanzado para lead %s", lead_id)

    if not respuesta_texto:
        logger.warning("Respuesta vacía de Claude para lead %s — no se envía nada", lead_id)
        return

    enviar_texto(lead.telefono, respuesta_texto)
    Mensaje.objects.create(lead=lead, rol=Mensaje.Rol.BOT, contenido=respuesta_texto)

    # Respaldo determinista: si Claude no escaló pero los datos mínimos están
    # completos y el lead sigue en conversación, escalamos de todos modos.
    d = lead.datos_viaje
    if not escalado and lead.estado == Lead.Estado.EN_CONVERSACION \
            and d.get("destino") and d.get("fecha_inicio") and d.get("num_personas"):
        logger.info("Escalamiento por respaldo (datos completos) para %s", lead.nombre)
        escalado = True

    if escalado:
        _post_escalamiento(lead)


def _construir_historial(lead):
    """Convierte los últimos mensajes de la BD al formato de la API de Claude.

    IMPORTANTE para el caching: el contenido de cada mensaje se arma SIEMPRE
    como lista de bloques (nunca como string plano), aunque solo el último
    bloque termine llevando cache_control. Si un mensaje se representa como
    string plano en un turno y como lista de bloques en el siguiente (porque
    en ese momento era "el último"), el prefijo deja de ser byte-idéntico y
    Anthropic no reconoce el cache -- eso es lo que estaba pasando antes:
    cache_write en cada turno, cache_read siempre en 0.
    """
    mensajes = list(
        lead.mensajes.exclude(rol=Mensaje.Rol.SISTEMA).order_by("-created_at")[:MAX_HISTORIAL]
    )[::-1]

    historial = []
    for m in mensajes:
        rol = "user" if m.rol == Mensaje.Rol.CLIENTE else "assistant"
        if historial and historial[-1]["role"] == rol:
            # concatenar en el texto del último bloque existente, no en un string aparte
            historial[-1]["content"][-1]["text"] += f"\n{m.contenido}"
        else:
            historial.append({"role": rol, "content": [{"type": "text", "text": m.contenido}]})

    while historial and historial[0]["role"] != "user":
        historial.pop(0)
    return historial


def _ejecutar_tool(lead, nombre, inputs):
    if nombre == "registrar_datos_viaje":
        datos = {k: v for k, v in inputs.items() if v}
        lead.datos_viaje = {**lead.datos_viaje, **datos}
        lead.save(update_fields=["datos_viaje", "updated_at"])
        logger.info("Datos de viaje actualizados para %s: %s", lead.nombre, datos)
        return {"ok": True, "datos_actuales": lead.datos_viaje}

    if nombre == "escalar_a_asesor":
        logger.info("Escalando lead %s — motivo: %s", lead.nombre, inputs.get("motivo"))
        return {"ok": True}

    return {"ok": False, "error": f"Tool desconocida: {nombre}"}


def _post_escalamiento(lead):
    """Marca el lead como calificado y notifica al asesor.
    El bot NUNCA se pausa automáticamente — sigue respondiendo en modo
    secundario (ver sección del system prompt para leads calificados/cotizados)."""
    from .whatsapp import enviar_texto

    lead.estado = Lead.Estado.CALIFICADO
    lead.save(update_fields=["estado", "updated_at"])

    Mensaje.objects.create(
        lead=lead, rol=Mensaje.Rol.SISTEMA,
        contenido="Lead escalado a asesor. Bot sigue activo en modo secundario.",
    )

    import os
    asesor_tel = os.environ.get("ASESOR_WHATSAPP")
    if asesor_tel:
        d = lead.datos_viaje
        resumen = (
            f"🔔 Nuevo lead calificado\n"
            f"*{lead.nombre}* — {lead.telefono}\n"
            f"📍 {d.get('destino', '?')} · 📅 {d.get('fecha_inicio', '?')} a {d.get('fecha_fin', '?')} · "
            f"👥 {d.get('num_personas', '?')} · 💰 {d.get('presupuesto', 'no indicó')}\n"
            f"📝 {d.get('notas', '—')}"
        )
        try:
            enviar_texto(asesor_tel, resumen)
        except Exception:
            logger.exception("No se pudo notificar al asesor")