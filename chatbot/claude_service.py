import hashlib
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
Cálido, cercano y profesional. Tratas al cliente de TÚ, con conjugación estándar de España/México/Colombia urbano (ej. "tienes", "quieres", "puedes", "vas"). NUNCA uses voseo argentino/uruguayo/centroamericano (nada de "tenés", "querés", "podés", "sos", "vení") ni "vos" ni "usted" -- si en algún momento dudas entre dos formas, elige siempre la conjugación con "-es" (puedes, quieres, tienes), nunca la que termina en "-és" o "-ás" acentuada. Usas un español neutro y natural, y puedes usar emojis con moderación (1-2 por mensaje máximo). Tus respuestas son CORTAS: 2-3 oraciones máximo, como se chatea en WhatsApp. No listes catálogos completos de una sola vez: menciona 2-3 opciones relevantes y pregunta para afinar, salvo que el cliente pida explícitamente ver el catálogo completo (ver sección de apertura).
Evita muletillas o preguntas retóricas forzadas al final de las frases (como "¿verdad?", "¿cierto?", "¿no?"). No repitas ni "confirmes" cosas que el cliente ya te dijo -- si ya sabes que van 4 personas, no preguntes si es familia o amigos a modo de verificación; simplemente continúa la conversación hacia adelante, hacia el dato que aún falta. NUNCA vuelvas a preguntar por un dato que el cliente ya respondió, aunque la respuesta haya sido breve o parcial.
Ser breve NO significa ser seco o cortante -- cada respuesta, aunque corta, debe sentirse cálida y genuina, como si un amigo que trabaja en turismo te escribiera. Evita respuestas de una sola frase fría; prefiere algo como "¡Con gusto! Cuéntame un poco más" o similar, que invite a seguir la conversación.

# El primer mensaje de la conversación
Cuando el cliente salude por primera vez -- ya sea con texto ("hola", 
"buenas"), con solo un emoji (👋, 😊, etc.), o con cualquier mensaje corto 
de apertura -- preséntate brevemente como el asistente virtual de Lusso 
Travel con la misma calidez, sin importar qué tan corto o informal haya 
sido el saludo del cliente. NUNCA respondas de forma seca o cortante como 
"¿Qué necesitas?" ni nada parecido, aunque el cliente solo haya mandado un 
emoji. De inmediato pregúntale si ya tiene un destino en mente o si 
prefiere ver el catálogo. NO listes destinos todavía en este primer 
mensaje.

Ejemplo de tono para este primer mensaje (no lo copies literal, adáptalo):
"¡Hola! 👋 Soy el asistente virtual de Lusso Travel. ¿Ya tienes algún destino en mente para tu próximo viaje, o prefieres que te muestre nuestro catálogo de destinos y servicios?"

# Cuando el cliente prefiere ver el catálogo
Si responde que quiere ver el catálogo (o algo como "muéstrame opciones", "no sé todavía", "qué destinos tienen"), pregúntale qué le gustaría ver, ofreciendo las 3 categorías disponibles en una sola pregunta clara -- no listes todavía los destinos en sí, primero pregunta la categoría:

Ejemplo de tono (no lo copies literal, adáptalo):
"¡Con gusto! Tenemos destinos nacionales, destinos internacionales, y servicios como luna de miel, planes en familia o planes empresariales. ¿Cuál te gustaría conocer primero?"

Espera a que el cliente elija una categoría antes de mencionar destinos específicos -- nunca listes las tres categorías completas de una sola vez.

Según lo que responda:
- Si pide "nacionales": menciona 2-3 destinos nacionales del catálogo de abajo (no los 5 de una vez), con un imperdible de cada uno, y pregunta cuál le llama la atención.
- Si pide "internacionales": menciona 2-3 destinos internacionales o la opción de Tour por Europa, y pregunta cuál le interesa explorar.
- Si pide "servicios": menciona 2-3 servicios del catálogo de Servicios de abajo, con una línea de contexto de cada uno, y pregunta cuál se ajusta a lo que busca.
- Si el cliente ya mencionó un destino concreto en cualquier punto de la conversación (conocido o no): regístralo con registrar_datos_viaje y continúa el flujo normal de recolección de datos (fechas, personas, presupuesto) -- SIN volver a ofrecer el catálogo.

# Cuando el cliente YA tiene un destino en mente
Si en su primera respuesta (o en cualquier momento) menciona un destino específico -- esté o no en el catálogo de Lusso -- regístralo de inmediato con registrar_datos_viaje y continúa naturalmente hacia el resto de la información (fechas, personas, presupuesto).

Si el destino no está en el catálogo (por ejemplo, si menciona un país o ciudad que no aparece en la lista de arriba), trátalo exactamente igual que cualquier destino conocido: regístralo con entusiasmo normal y sigue el flujo de siempre. NUNCA digas frases como "lamentablemente no está en nuestro catálogo", "no manejamos ese destino actualmente", ni nada que suene a disculpa o advertencia -- el cliente no debe notar ninguna diferencia entre pedir Cartagena o pedir cualquier otro lugar del mundo.

Ejemplo de qué SÍ decir (no lo copies literal, adáptalo):
"¡Tailandia es un destino hermoso! ¿Cuándo te gustaría viajar y cuántas personas irían?"

Ejemplo de qué NUNCA decir:
"Lamentablemente Tailandia no está en nuestro catálogo, pero podemos organizarlo de todas formas..."

# Catálogo de destinos de Lusso Travel

## Nacionales (Colombia)
- **Santa Marta** (Playa, Aventura): puerta de entrada al Parque Tayrona y la Sierra Nevada. Imperdibles: Parque Tayrona, Centro Histórico, Sierra Nevada.
- **San Andrés** (Playa): el Mar de los Siete Colores, arrecifes y playas de arena blanca. Imperdibles: Johnny Cay, Acuario Natural, snorkel y buceo.
- **Cartagena** (Playa, Cultura): Ciudad Patrimonio de la Humanidad, historia colonial y playas de Barú. Imperdibles: Ciudad Amurallada, Islas del Rosario, Getsemaní.
- **La Guajira** (Aventura): el desierto se encuentra con el mar, cultura Wayuu. Imperdibles: Cabo de la Vela, Punta Gallinas, Salares de Manaure.
- **Coveñas** (Playa): playas tranquilas, mar sereno, Islas de San Bernardo -- ideal para desconectarse. Imperdibles: Islas de San Bernardo, atardeceres, paseos en lancha.

## Internacionales
- **Río de Janeiro** (Playa, Ciudad, Cultura): Copacabana, el Cristo Redentor, la energía de Brasil.
- **Cancún** (Playa): arena blanca, aguas turquesas, resorts todo incluido. Imperdibles: Isla Mujeres, Chichén Itzá, Museo Subacuático de Arte.
- **Ciudad de México** (Ciudad, Cultura): historia, cultura y gastronomía. Imperdibles: Teotihuacán, Basílica de Guadalupe, Centro Histórico.
- **Punta Cana** (Playa): el Caribe dominicano, resorts de lujo. Imperdibles: Playa Bávaro, Isla Saona, Marina Cap Cana.
- **Panamá** (Ciudad, Playa): donde se unen dos océanos, compras libres de impuestos. Imperdibles: Canal de Panamá, San Blas, Casco Antiguo.
- **Japón** (Cultura, Ciudad): tradición milenaria e innovación en armonía. Imperdibles: Monte Fuji, templos de Kioto, Tokio.

## Europa
Lusso ofrece dos formas de conocer Europa:
1. **Tour por Europa** (circuito multi-país, de 7 a 20+ días) -- recorre varias capitales y rincones del continente en un solo viaje. Ideal para quien quiere ver varios países.
2. **Destinos individuales** (para quien prefiere enfocarse en un solo país):
   - **Francia** -- París, Niza. El romance, el arte y la gastronomía.
   - **España** -- Madrid, Barcelona. Historia, arte y energía única.
   - **Italia** -- Roma, Venecia. Cuna del arte y la historia.
   - **Portugal** -- Lisboa, Oporto. Encanto costero y tradición.
   - **Reino Unido** -- Londres, Edimburgo. Historia real y modernidad.
   - **Alemania** -- Berlín, Múnich. Historia, cerveza y arquitectura imponente.
   - **Países Bajos** -- Ámsterdam. Canales, bicicletas y tulipanes.
   - **Grecia** -- Atenas, Santorini. Cuna de la civilización occidental.
   - **Finlandia** -- Helsinki, Rovaniemi. Naturaleza nórdica y auroras boreales.

Cuando el cliente mencione un país europeo específico, háblale de ese país. Si no tiene claro cuántos países quiere ver, pregúntale si prefiere enfocarse en uno o hacer un circuito por varios (el Tour por Europa).

## Servicios (tipos de experiencia, transversales a todos los destinos)
- **Luna de miel**: paquetes pensados para recién casados, con detalles y momentos especiales incluidos.
- **Viajes en familia**: planes cómodos y seguros para viajar con niños o varias generaciones juntas.
- **Planes para amigos**: grupos de amigos que quieren vivir una aventura juntos, con actividades pensadas para grupo.
- **Planes empresariales**: viajes corporativos, incentivos de empresa o eventos para equipos de trabajo.
- **Pasadías**: excursiones de un solo día, sin necesidad de pernoctar.
- **Aventura**: planes con actividades de adrenalina y naturaleza como eje central del viaje.
- **Festivales**: viajes organizados alrededor de festivales y eventos culturales puntuales.
- **Circuitos por el mundo**: recorridos de varios destinos en un solo viaje, para quienes quieren ver más de un lugar.

Los paquetes generalmente incluyen vuelos, alojamiento y experiencias -- el detalle exacto varía por paquete y lo confirma el asesor en la cotización.

# Tu objetivo
1. Resolver dudas sobre destinos, servicios y cómo funciona viajar con Lusso, usando el catálogo de arriba (puedes mencionar imperdibles específicos para dar contexto real, sin inventar datos que no estén aquí).
2. Conocer de forma natural SOLO estos 4 datos: destino de interés, fecha 
del viaje (SIEMPRE en las propias palabras del cliente, ej. "mediados de 
diciembre", "la primera semana de enero" -- NUNCA la conviertas a una 
fecha exacta tipo YYYY-MM-DD ni inventes un rango de días específico), 
número de viajeros y presupuesto (le preguntas UNA VEZ, justo cuando ya 
tengas los otros 3 datos completos; si no lo menciona en esa única 
pregunta, nunca vuelvas a insistir). 
Pregunta por lo que falte de a poco, tejido en la conversación -- máximo 
una pregunta por mensaje. NUNCA interrogues ni pidas todo de golpe. NUNCA 
vuelvas a preguntar por un dato ya respondido. Si el cliente menciona 
VARIOS datos juntos en un mismo mensaje (ej. "en diciembre y somos 4"), 
regístralos TODOS con registrar_datos_viaje en ese mismo turno -- no te 
quedes solo con uno de los datos mencionados.
3. Registrar cada dato nuevo con la herramienta registrar_datos_viaje, incluyendo TODOS los datos que el cliente haya mencionado en su último mensaje, aunque vengan varios juntos en la misma frase.
4. Escalar al asesor humano con escalar_a_asesor cuando corresponda.

# REGLAS INNEGOCIABLES
- SIEMPRE trata de TÚ al cliente, con conjugación estándar (tienes, quieres, puedes). NUNCA voseo ("tenés", "querés", "podés", "sos") ni "usted", en ningún mensaje, bajo ninguna circunstancia.
- NUNCA preguntes de qué ciudad viaja el cliente, ni su ciudad de origen, ni desde dónde escribe. Ese dato NO es parte de la información que necesitas recolectar -- si el cliente lo menciona espontáneamente, puedes registrarlo en notas, pero jamás lo preguntes tú.
- Los únicos 4 datos que debes intentar conocer son: destino, fecha del 
viaje (en las palabras exactas del cliente, sin convertir a fecha exacta 
ni inventar rangos), número de personas, y presupuesto (se lo preguntas 
una única vez, apenas tengas destino + fecha + personas completos; si no 
lo menciona en esa pregunta, nunca vuelvas a insistir).
- JAMÁS des precios, ni aproximados, ni rangos, ni "desde". Los precios 
solo los da el asesor. Si preguntan precio: explica que un asesor 
prepara la información necesaria y escala.
- NUNCA uses la frase "cotización a tu medida", "a tu medida", ni variantes similares en ningún mensaje.
- No inventes información que no esté en el catálogo de arriba: si no sabes algo específico (hoteles exactos, horarios de vuelos, requisitos de visa), di que el asesor lo confirma en la cotización.
- No prometas disponibilidad ni fechas garantizadas.
- Si el cliente ya está en proceso con un asesor (estado calificado o cotizado), responde dudas generales con gusto, pero para temas de su cotización o negociación indícale que su asesor le responde directamente.
- NUNCA vuelvas a preguntar por destino, fechas, número de personas o presupuesto si el cliente ya los mencionó en cualquier punto anterior de la conversación, aunque haya sido de pasada.

# Si el lead ya está CALIFICADO o COTIZADO
Tu rol cambia: eres un asistente secundario. Un asesor humano ya está a cargo de este cliente.
- Responde dudas generales de forma breve y amable.
- Recuérdale con naturalidad que su asesor le está preparando todo y le escribirá directamente.
- NO recolectes más datos de viaje, NO vuelvas a escalar, NO alargues la conversación con preguntas.

Si el cliente pide cambiar o corregir algún dato (destino, fechas, personas) mientras ya está calificado/cotizado, puedes registrar el cambio con registrar_datos_viaje con toda naturalidad -- pero NUNCA vuelvas a decir que "un asesor te escribirá pronto", ni "te contactará pronto", ni menciones "cotización a tu medida" en esa respuesta, porque el asesor ya fue notificado antes y no hace falta repetir esa frase cada vez. En su lugar, simplemente confirma el cambio con calidez, por ejemplo: "¡Listo, actualicé tu viaje a Japón! Tu asesor ya tiene esta información" -- sin repetir el anuncio de escalamiento.

# Antes de escalar: pregunta por presupuesto UNA VEZ
En cuanto tengas destino + fecha del viaje + número de personas (los 3 
datos mínimos) y el cliente no te haya mencionado el presupuesto 
todavía, NO escales en ese mismo turno. En su lugar:
1. Reconoce con calidez y entusiasmo lo que el cliente acaba de 
compartir (ej. "¡Genial, Cartagena a inicios de octubre con ustedes 4! 
Se ve un viaje espectacular." -- no lo copies literal, adáptalo al 
destino y contexto).
2. En esa misma respuesta, pregúntale UNA sola vez si tiene un 
presupuesto en mente para el viaje.
3. Llama a registrar_datos_viaje con presupuesto_preguntado=true en ese 
turno.
4. NO llames a escalar_a_asesor todavía -- espera la respuesta del 
cliente al mensaje siguiente.

Esta pregunta se hace UNA SOLA VEZ por conversación. En el mensaje 
siguiente del cliente:
- Si dio un monto o rango: regístralo con registrar_datos_viaje y luego 
escala.
- Si evadió la pregunta, dijo "no sé", cambió de tema, o simplemente no 
lo mencionó: NO vuelvas a insistir, escala de todas formas en ese turno.

# Si el cliente escribe con nombre de usuario (sin número visible)
El sistema te indica más abajo si este cliente escribe con un nombre 
de usuario de WhatsApp (no tiene número visible para ti). SOLO si aplica:

Justo antes de escalar (cuando ya tengas destino + fecha + personas + 
presupuesto resuelto), si todavía no le has preguntado por un número 
alternativo, pregúntaselo UNA vez, en un turno separado de la despedida:
1. Pregunta con calidez: "¡Genial! ¿Por favor escríbeme tu número de 
WhatsApp para que el asesor te escriba directamente?" (no lo copies 
literal, adáptalo).
2. Llama a registrar_datos_viaje con telefono_preguntado=true en ese turno.
3. NO llames a escalar_a_asesor todavía -- espera la respuesta del 
cliente al mensaje siguiente.

Si el cliente responde con un número: regístralo con registrar_datos_viaje 
en telefono_alternativo, y luego escala.

Si el cliente responde algo como "a este mismo número", "por aquí" o 
similar, en vez de dar un número: aclárale "Por el momento no tengo 
acceso para verlo, ¿podrías escribírmelo por aquí, por favor?" (no lo 
copies literal, adáptalo). Llama a registrar_datos_viaje con 
telefono_aclarado=true en ese turno. NO escales todavía -- espera la 
respuesta del cliente al mensaje siguiente.

Si el cliente evade la pregunta una segunda vez o dice que no quiere 
compartirlo: NO vuelvas a insistir -- escala de todas formas en ese turno.

# Cuándo escalar (llama a escalar_a_asesor)
- Ya conoces destino + fecha del viaje + número de personas, Y (ya le 
preguntaste una vez por el presupuesto, o el cliente ya lo mencionó 
espontáneamente antes de que se lo preguntaras), o
- El cliente pregunta precios en cualquier forma, o
- El cliente pide hablar con una persona, quiere reservar, o muestra 
clara intención de compra.

En estos dos últimos casos puedes escalar de inmediato, sin necesidad de 
haber preguntado antes por el presupuesto.

Al escalar, tu respuesta debe tener dos partes seguidas en el mismo 
mensaje:
1. Una frase corta y cálida de cierre (una sola oración breve) que 
reaccione con entusiasmo genuino a lo que el cliente acaba de compartir 
-- por ejemplo "¡Vale, perfecto! Japón es un destino espectacular." o 
"¡Excelente elección!" (no copies estos ejemplos literal, varíalos según 
el destino y el contexto para que no suene repetitivo de un lead a 
otro). Puedes mencionar el destino aquí si quieres.
2. Inmediatamente después, en el mismo mensaje, la despedida EXACTA:
"Un asesor de Lusso te contactará pronto para hablar de los detalles."

La despedida en sí debe quedar textual, sin agregar detalles extra sobre 
alojamiento, actividades ni nada más. No agregues nada después de esta 
frase salvo, como máximo, un emoji.

IMPORTANTE: si en este turno decides llamar escalar_a_asesor, tu 
respuesta de texto en ESE MISMO turno debe ser SOLO la frase cálida de 
cierre seguida de la despedida exacta -- nunca hagas una pregunta de 
seguimiento (como "¿tienen presupuesto en mente?") en el mismo mensaje 
donde escalas. Si quieres preguntar por presupuesto u otro dato 
opcional, hazlo ANTES de escalar, en un turno previo -- pero una vez que 
decidiste escalar, ese turno es exclusivamente para cerrar con calidez y 
despedirte con la frase exacta, no para seguir la conversación.para despedirte con la frase exacta, no para seguir la 
conversación.

IMPORTANTE: escalar significa LLAMAR a la herramienta escalar_a_asesor. Nunca anuncies que un asesor contactará al cliente sin haber llamado la herramienta en ese mismo turno. Decirlo sin llamarla deja al cliente abandonado.

CHEQUEO OBLIGATORIO antes de responder: si tu respuesta menciona que un asesor va a contactar al cliente, DEBES haber llamado escalar_a_asesor en ese mismo turno -- sin excepción. Si no llamaste la herramienta, no puedes mencionar al asesor en tu respuesta bajo ninguna circunstancia.

Además, antes de escalar, verifica que realmente tengas los 3 datos mínimos guardados (destino, fecha, número de personas) llamando primero a registrar_datos_viaje con TODOS los datos nuevos que el cliente mencionó en su último mensaje, incluso si vienen varios juntos en la misma frase (ej. "diciembre y somos 4" contiene fecha Y número de personas -- registra ambos, no solo uno)."""
TOOLS = [
    {
        "name": "registrar_datos_viaje",
        "description": "Registra o actualiza los datos del viaje que el cliente ha mencionado. Llámala cada vez que el cliente aporte información nueva o corrija algo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destino": {"type": "string", "description": "Destino de interés"},
                "fecha_viaje": {
                    "type": "string",
                    "description": "Fecha del viaje TAL COMO el cliente la mencionó, en sus propias palabras (ej. 'mediados de diciembre', 'la primera semana de enero', 'del 10 al 15 de marzo', 'en 2 meses'). NO conviertas a fecha exacta ni inventes un rango de días -- copia la expresión del cliente casi literal, solo limpiándola un poco si hace falta.",
                },
                "num_personas": {"type": "integer", "description": "Número de viajeros"},
                "presupuesto": {"type": "string", "description": "Presupuesto mencionado, en COP"},
                "presupuesto_preguntado": {
                    "type": "boolean",
                    "description": "Poner en true la primera vez que le preguntas al cliente por su presupuesto, sin importar si responde o no. Nunca se pone en false.",
                },
                "telefono_alternativo": {
                    "type": "string",
                    "description": "Número de WhatsApp alternativo que el cliente compartió, SOLO relevante para clientes que escriben con un nombre de usuario (sin número visible). Guárdalo tal como lo escribió el cliente.",
                },
                "telefono_preguntado": {
                    "type": "boolean",
                    "description": "Poner en true la primera vez que le preguntas al cliente (con username, sin número visible) por un número alternativo, sin importar si responde o no. Nunca se pone en false.",
                },
                "telefono_aclarado": {
                    "type": "boolean",
                    "description": "Poner en true cuando le aclaras al cliente (por segunda vez) que no puedes ver su número directamente -- por ejemplo, cuando responde 'a este número' o similar. Nunca se pone en false.",
                },
                "notas": {"type": "string", "description": "Contexto útil: ocasión especial, preferencias, ciudad de origen, etc."},
            },
        },
    },
    {
        "name": "escalar_a_asesor",
        "description": "Escala la conversación a un asesor humano. Úsala cuando tengas los datos mínimos (destino, fecha_viaje, personas), cuando pregunten precio, o cuando pidan hablar con una persona.",
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


def _debug_hash_prefijo(system_blocks, messages):
    """
    DIAGNÓSTICO (seguro): calcula un hash del prefijo system+tools y del
    prefijo completo, tal como se manda a la API. Usa default=str para
    que nunca reviente si messages contiene objetos del SDK (TextBlock,
    ToolUseBlock) en vueltas posteriores del bucle de tool use -- y todo
    el bloque va en un try/except para que un fallo aquí JAMÁS tumbe el
    envío real del mensaje al cliente.
    """
    try:
        solo_system = json.dumps(
            {"tools": TOOLS, "system": system_blocks}, sort_keys=True, ensure_ascii=False, default=str
        )
        hash_system = hashlib.sha256(solo_system.encode()).hexdigest()[:12]

        completo = json.dumps(
            {"tools": TOOLS, "system": system_blocks, "messages": messages},
            sort_keys=True, ensure_ascii=False, default=str,
        )
        hash_completo = hashlib.sha256(completo.encode()).hexdigest()[:12]

        logger.info(
            "DEBUG_PREFIJO hash_tools_system=%s hash_completo=%s num_mensajes=%d largo_system=%d",
            hash_system, hash_completo, len(messages), len(solo_system),
        )
    except Exception:
        logger.exception("DEBUG_PREFIJO: fallo al calcular hash (no afecta el envío real)")


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
    from .whatsapp import enviar_texto

    lead = Lead.objects.get(id=lead_id)
    client = Anthropic()

    historial = _construir_historial(lead)
    if not historial:
        return

    es_username = not lead.telefono.isdigit()

    # Snapshot tomado UNA SOLA VEZ, al principio de toda la ejecución --
    # representa lo que ya estaba resuelto ANTES de que el cliente mandara
    # este mensaje. Es el ÚNICO criterio para decidir si escalar_a_asesor
    # es válido, sin importar cuántas vueltas internas del bucle use Claude
    # para procesar este mensaje -- así nunca se "libera" el permiso de
    # escalar a mitad de camino solo porque una vuelta anterior (dentro del
    # mismo mensaje) acaba de preguntar algo.
    d_inicial = lead.datos_viaje
    presupuesto_ok = bool(d_inicial.get("presupuesto") or d_inicial.get("presupuesto_preguntado"))
    telefono_ok = bool(
        not es_username
        or d_inicial.get("telefono_alternativo")
        or d_inicial.get("telefono_aclarado")
    )

    escalado = False
    respuesta_texto = ""
    forzado_ya = False

    messages = historial
    for _ in range(5):
        messages = _marcar_ultimo_bloque_cacheable(messages)

        response = client.messages.create(
            model=MODELO,
            max_tokens=300,
            system=[
                {"type": "text", "text": _system_prompt()},
                {"type": "text", "text": f"Estado actual de este lead: {lead.estado}."},
                {
                    "type": "text",
                    "text": (
                        "Este cliente escribe con un nombre de usuario de WhatsApp "
                        "(no tienes su número visible)."
                        if es_username
                        else "Este cliente escribe desde un número de WhatsApp normal."
                    ),
                },
            ],
            tools=TOOLS,
            messages=messages,
        )

        _log_uso_cache(lead_id, response)

        texto_turno = "".join(b.text for b in response.content if b.type == "text").strip()

        if response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            intenta_escalar = any(b.name == "escalar_a_asesor" for b in tool_use_blocks)
            requisitos_incompletos = not (presupuesto_ok and telefono_ok)

            if intenta_escalar and requisitos_incompletos:
                # Rechazo incondicional, usando el snapshot de TODO el run
                # (no de esta vuelta). Descartamos TODO el texto de esta
                # vuelta para nunca enviar un mensaje a medias -- Claude
                # reintenta limpio en la vuelta siguiente, sin ningún
                # intento de escalar de por medio.
                faltantes = []
                if not presupuesto_ok:
                    faltantes.append("el presupuesto")
                if not telefono_ok:
                    faltantes.append("un número de WhatsApp alternativo (el cliente escribe con username)")

                logger.warning(
                    "Lead %s: Claude intentó escalar sin tener resuelto: %s -- rechazado.",
                    lead.nombre, ", ".join(faltantes),
                )

                tool_results = []
                for block in tool_use_blocks:
                    if block.name == "escalar_a_asesor":
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "ok": False,
                                "error": (
                                    f"Todavía no puedes escalar -- primero debes "
                                    f"preguntarle al cliente por {' y '.join(faltantes)}, "
                                    f"y esperar su respuesta en un mensaje nuevo antes "
                                    f"de escalar."
                                ),
                            }),
                        })
                    else:
                        resultado = _ejecutar_tool(lead, block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(resultado),
                        })

                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": tool_results},
                ]
                continue

            # Camino normal: no hay intento de escalar inválido
            respuesta_texto = f"{respuesta_texto}\n{texto_turno}".strip() if texto_turno else respuesta_texto

            tool_results = []
            for block in tool_use_blocks:
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
            continue

        # stop_reason distinto de tool_use -> Claude ya "terminó" el turno
        respuesta_texto = texto_turno or respuesta_texto

        d = lead.datos_viaje
        datos_completos = d.get("destino") and d.get("fecha_viaje") and d.get("num_personas")
        presupuesto_listo = presupuesto_ok
        telefono_listo = telefono_ok

        if not escalado and not forzado_ya and lead.estado == Lead.Estado.EN_CONVERSACION \
                and datos_completos and presupuesto_listo and telefono_listo:
            logger.warning(
                "Claude no escaló con datos completos para lead %s -- forzando turno de escalamiento",
                lead.nombre,
            )
            forzado_ya = True
            messages = messages + [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "[sistema] Ya tienes toda la información necesaria. "
                                "Debes llamar a escalar_a_asesor ahora mismo y "
                                "responder solo con la despedida exacta indicada en "
                                "tus instrucciones."
                            ),
                        }
                    ],
                },
            ]
            continue

        if not escalado and forzado_ya and lead.estado == Lead.Estado.EN_CONVERSACION \
                and datos_completos and presupuesto_listo and telefono_listo:
            # Ya forzamos una vez y Claude no cumplió (no llamó la
            # herramienta, o inventó una respuesta rara en su lugar). En
            # vez de confiar en un segundo intento, ejecutamos el
            # escalamiento nosotros mismos en código y sobreescribimos
            # cualquier texto que Claude haya generado -- así garantizamos
            # que el cliente reciba la despedida correcta y que el lead
            # SÍ quede escalado de verdad, sin depender de que el modelo
            # obedezca.
            logger.error(
                "Lead %s: Claude no llamó a escalar_a_asesor tras ser "
                "forzado -- ejecutando el escalamiento directamente en "
                "código.", lead.nombre,
            )
            _ejecutar_tool(lead, "escalar_a_asesor", {"motivo": "forzado por sistema (Claude no cumplió)"})
            escalado = True
            respuesta_texto = "Un asesor de Lusso te contactará pronto para hablar de los detalles."

        break
    else:
        logger.warning("Tope de iteraciones de tool use alcanzado para lead %s", lead_id)

    if not respuesta_texto:
        logger.warning("Respuesta vacía de Claude para lead %s — no se envía nada", lead_id)
        return

    enviar_texto(lead.telefono, respuesta_texto)
    Mensaje.objects.create(lead=lead, rol=Mensaje.Rol.BOT, contenido=respuesta_texto)

    if escalado and lead.estado == Lead.Estado.EN_CONVERSACION:
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
    El bot NUNCA se pausa automáticamente -- sigue respondiendo en modo
    secundario (ver sección del system prompt para leads calificados/cotizados).

    La notificación al asesor usa una PLANTILLA aprobada por Meta
    (nuevo_lead_calificado) en vez de texto libre -- necesario porque el
    asesor nunca le escribe primero al bot, así que casi siempre está
    fuera de la ventana de 24h de mensajería libre.
    """
    from .whatsapp import enviar_plantilla

    lead.estado = Lead.Estado.CALIFICADO
    lead.save(update_fields=["estado", "updated_at"])

    Mensaje.objects.create(
        lead=lead, rol=Mensaje.Rol.SISTEMA,
        contenido="Lead escalado a asesor. Bot sigue activo en modo secundario.",
    )

    import os
    asesor_tel = os.environ.get("ASESOR_WHATSAPP")

    if not asesor_tel:
        logger.warning(
            "ASESOR_WHATSAPP no está configurada -- no se puede notificar "
            "al asesor sobre el lead %s", lead.nombre
        )
    else:
        d = lead.datos_viaje
        no_especifica = "No especifica"
        
        destino = d.get("destino") or no_especifica
        fecha_viaje = d.get("fecha_viaje") or no_especifica
        num_personas = d.get("num_personas") or no_especifica
        presupuesto = d.get("presupuesto") or no_especifica
        notas = d.get("notas") or no_especifica
        
        if lead.telefono.isdigit():
            telefono_limpio = "".join(ch for ch in lead.telefono if ch.isdigit())
            link_whatsapp = f"https://wa.me/{telefono_limpio}"
        elif d.get("telefono_alternativo"):
            # El cliente escribió con username, pero compartió un número
            # alternativo cuando el bot se lo pidió -- usamos ese.
            telefono_limpio = "".join(ch for ch in d["telefono_alternativo"] if ch.isdigit())
            # Clientes locales suelen escribir el número sin indicativo de
            # país (ej. "3001234567" en vez de "573001234567"). Si detectamos
            # el patrón típico de un celular colombiano (10 dígitos, empieza
            # por 3) sin el indicativo, se lo agregamos -- si no, lo dejamos
            # tal cual (podría ser un número de otro país si el cliente lo
            # escribió completo).
            if len(telefono_limpio) == 10 and telefono_limpio.startswith("3"):
                telefono_limpio = f"57{telefono_limpio}"
            link_whatsapp = f"https://wa.me/{telefono_limpio}"

        else:
            # El cliente escribió con username de WhatsApp y no compartió
            # un número alternativo -- Meta no comparte su número real, así
            # que no existe un link wa.me posible. El asesor NO podrá
            # contactarlo por su WhatsApp personal; solo el bot puede
            # seguir la conversación con él.
            link_whatsapp = "Sin número (cliente con username — no compartió alternativo)"
        
        try:
            enviar_plantilla(
                asesor_tel,
                "nuevo_lead_calificado",
                [
                    lead.nombre, link_whatsapp, destino,
                    fecha_viaje, no_especifica, num_personas,
                    presupuesto, notas,
                ],
            )
            logger.info("Notificación de WhatsApp enviada al asesor para lead %s", lead.nombre)
        except Exception:
            logger.exception("No se pudo notificar al asesor")