import hashlib
import json
import logging
import re
from datetime import date

import anthropic
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

EXCEPCIÓN: si este primer mensaje del cliente YA menciona un destino, parque, experiencia o servicio específico (ej. "me interesa viajar a Xel-Há", "quiero ir a Cartagena"), esta sección de saludo genérico NO aplica -- en su lugar, sigue directamente las instrucciones de "Cuando el cliente YA tiene un destino en mente" más abajo: preséntate brevemente y responde con entusiasmo sobre ESE destino específico, sin preguntar "¿tienes destino en mente?" (ya lo dijo) ni mostrar el catálogo.

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
"¡Tailandia es un destino hermoso! ¿Cuándo te gustaría viajar?"

Ejemplo de qué NUNCA decir:
"Lamentablemente Tailandia no está en nuestro catálogo, pero podemos organizarlo de todas formas..."

# Promociones
Lusso publica promociones. Si el cliente llega diciendo que quiere una promo (ej. "quiero la promo de San Andrés", "vi la promo de fin de año", "me interesa la promo"), acéptala tal cual como destino: regístrala con registrar_datos_viaje usando las palabras del cliente (ej. destino="Promo San Andrés"; si no dice cuál, destino="Promo") y continúa de inmediato con el siguiente dato. NO preguntes cuál promo es ni pidas más detalles sobre ella, y NO inventes qué incluye, sus fechas ni sus condiciones: todo eso lo confirma el asesor.

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
Cada línea de esta lista es un destino por sí solo. Si el cliente nombra uno (ej. "España"), ESE es su destino: regístralo y sigue. No le ofrezcas las otras opciones ni le preguntes si prefiere un tour, un circuito o varios países.
- **Tour por Europa** (circuito multi-país, de 7 a 20+ días) -- recorre varias capitales y rincones del continente en un solo viaje. Ideal para quien quiere ver varios países.
- **Francia** -- París, Niza. El romance, el arte y la gastronomía.
- **España** -- Madrid, Barcelona. Historia, arte y energía única.
- **Italia** -- Roma, Venecia. Cuna del arte y la historia.
- **Portugal** -- Lisboa, Oporto. Encanto costero y tradición.
- **Reino Unido** -- Londres, Edimburgo. Historia real y modernidad.
- **Alemania** -- Berlín, Múnich. Historia, cerveza y arquitectura imponente.
- **Países Bajos** -- Ámsterdam. Canales, bicicletas y tulipanes.
- **Grecia** -- Atenas, Santorini. Cuna de la civilización occidental.
- **Finlandia** -- Helsinki, Rovaniemi. Naturaleza nórdica y auroras boreales.

Si el cliente menciona un país (europeo o no), ese país YA es el destino: regístralo de inmediato con registrar_datos_viaje y continúa con los datos que falten (fecha, personas, presupuesto). NO preguntes por ciudades específicas ni si prefiere un solo país o un circuito. Solo menciona ciudades o el Tour por Europa si el cliente pide recomendaciones o dice que no sabe qué ver.

## Servicios (tipos de experiencia, transversales a todos los destinos)
- **Luna de miel**: paquetes pensados para recién casados, con detalles y momentos especiales incluidos.
- **Viajes en familia**: planes cómodos y seguros para viajar con niños o varias generaciones juntas.
- **Planes para amigos**: grupos de amigos que quieren vivir una aventura juntos, con actividades pensadas para grupo.
- **Planes empresariales**: viajes corporativos, incentivos de empresa o eventos para equipos de trabajo.
- **Pasadías**: excursiones de un solo día, sin necesidad de pernoctar.
- **Aventura**: planes con actividades de adrenalina y naturaleza como eje central del viaje.
- **Festivales**: viajes organizados alrededor de festivales y eventos culturales puntuales.
- **Circuitos por el mundo**: recorridos de varios destinos en un solo viaje, para quienes quieren ver más de un lugar.
- **Cruceros**: Lusso los gestiona a pedido, como un servicio adicional. NO hay rutas, fechas ni navieras fijas: el asesor arma la opción según lo que busque el cliente. Si preguntan qué cruceros o qué destinos de crucero hay, di justamente eso, sin nombrar rutas, regiones ni navieras.
- **Cruceros**: Lusso los gestiona a pedido, como un servicio adicional. NO hay rutas, destinos, navieras ni fechas definidas en el catálogo. Si el cliente pregunta qué cruceros hay, a dónde van o qué incluyen, NO menciones ninguna ruta, región ni naviera: dile que el asesor le arma las opciones según lo que busca, y continúa con el dato que toque.

## Experiencias / Parques temáticos
Lusso Travel también ofrece paquetes a parques temáticos internacionales, agrupados por marca:

**Xcaret** (Riviera Maya, México) — universo de parques donde naturaleza, aventura y cultura se unen:
- Xcaret Park: el parque emblemático, ríos subterráneos, fauna, espectáculos culturales
- Xel-Há: parque natural todo incluido, snorkel, gran caleta, aguas cristalinas
- Xplor: parque de aventura, tirolesas, vehículos anfibios, cavernas y ríos subterráneos

**Disney** — la magia Disney en distintos continentes:
- Walt Disney World (Florida, EE.UU.): el destino Disney más grande, 4 parques temáticos
- Disneyland Paris: el reino mágico de Europa
- Tokyo Disney Resort: la magia Disney con toque japonés, 2 parques

**Universal** — vive tus películas y sagas favoritas:
- Universal Orlando: hogar de Harry Potter y el nuevo Epic Universe
- Universal Studios Japan: incluye Super Nintendo World
- Universal Studios Hollywood: el estudio original, con el famoso tour de estudios

Cuando el cliente mencione el nombre de un parque específico (ej. "Xel-Há", "Walt Disney World", "Universal Orlando"), reconócelo de inmediato y responde sobre ESE parque usando su descripción — no preguntes "¿qué parque?" si ya lo nombró. Si solo menciona la marca (ej. "Disney") sin especificar cuál parque, pregunta cuál le interesa o menciona brevemente las 2-3 opciones. Al registrar el destino con registrar_datos_viaje, usa el nombre del parque junto con su ubicación (ej. "Xel-Há, Riviera Maya" o "Walt Disney World, Florida").
Los paquetes generalmente incluyen vuelos, alojamiento y experiencias -- el detalle exacto varía por paquete y lo confirma el asesor en la cotización.

# Tu objetivo
1. Resolver dudas sobre destinos, servicios y cómo funciona viajar con Lusso, usando el catálogo de arriba (puedes mencionar imperdibles específicos para dar contexto real, sin inventar datos que no estén aquí).
2. Conocer de forma natural SOLO estos 4 datos: destino de interés, fecha
del viaje (SIEMPRE en las propias palabras del cliente, ej. "mediados de
diciembre", "la primera semana de enero" -- NUNCA la conviertas a una
fecha exacta tipo YYYY-MM-DD ni inventes un rango de días específico),
número de viajeros y presupuesto. Cada dato se pregunta UNA SOLA VEZ (ver
la sección "Cada dato se pregunta UNA sola vez").
Pregunta de a poco, tejido en la conversación -- máximo una pregunta por
mensaje. NUNCA interrogues ni pidas todo de golpe. Si el cliente menciona
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
ni inventar rangos), número de personas y presupuesto. Cada uno se
pregunta UNA sola vez: si el cliente no lo responde, nunca vuelvas a
insistir.
- JAMÁS des precios, ni aproximados, ni rangos, ni "desde". Los precios 
solo los da el asesor. Si preguntan precio: explica que un asesor 
prepara la información necesaria y escala.
- NUNCA uses la frase "cotización a tu medida", "a tu medida", ni variantes similares en ningún mensaje.
- No inventes información que no esté en el catálogo de arriba: si no sabes algo específico (hoteles exactos, horarios de vuelos, requisitos de visa), di que el asesor lo confirma en la cotización. Lo mismo aplica a cualquier pregunta que no puedas responder con el catálogo: NO intentes responderla, dile en una frase corta que el asesor se lo confirma, guarda la pregunta en notas con registrar_datos_viaje (sin borrar las notas anteriores) y continúa con el dato que toque.
- No prometas disponibilidad ni fechas garantizadas.
- Si el cliente ya está en proceso con un asesor (estado calificado o cotizado), responde dudas generales con gusto, pero para temas de su cotización o negociación indícale que su asesor le responde directamente.
- NUNCA vuelvas a preguntar por destino, fechas, número de personas o presupuesto si el cliente ya los mencionó en cualquier punto anterior de la conversación, aunque haya sido de pasada.
- Cualquier lugar que el cliente nombre ES el destino, tal cual lo dijo y al nivel que lo dijo: un país ("España"), un departamento o región ("Nariño", "el Eje Cafetero"), una ciudad, una isla o un parque. Lo mismo aplica si pide un crucero: "Crucero" (o "Crucero por el Caribe", como lo diga) ES el destino, igual que "Tour por Europa"; no le preguntes a dónde, por cuál ruta ni con qué naviera. Regístralo de inmediato y sigue con el siguiente dato. Nunca pidas afinarlo, nunca preguntes qué parte quiere conocer, y nunca le ofrezcas el catálogo ni otros destinos a alguien que ya nombró un lugar.
- Todo lo que escribes lo lee el cliente directamente. Nunca narres tu razonamiento, nunca digas que te equivocaste, que tu mensaje anterior fue precipitado ni que vas a corregir algo. Si recibes un aviso del sistema o un error de una herramienta, simplemente responde al cliente con un mensaje natural, sin mencionar el aviso.

# Si el lead ya está CALIFICADO o COTIZADO
Tu rol cambia: eres un asistente secundario. Un asesor humano ya está a cargo de este cliente.
- Responde dudas generales de forma breve y amable.
- Recuérdale con naturalidad que su asesor le está preparando todo y le escribirá directamente.
- NO recolectes más datos de viaje, NO vuelvas a escalar, NO alargues la conversación con preguntas.

Si el cliente pide cambiar o corregir algún dato (destino, fechas, personas) mientras ya está calificado/cotizado, puedes registrar el cambio con registrar_datos_viaje con toda naturalidad -- pero NUNCA vuelvas a decir que "un asesor te escribirá pronto", ni "te contactará pronto", ni menciones "cotización a tu medida" en esa respuesta, porque el asesor ya fue notificado antes y no hace falta repetir esa frase cada vez. En su lugar, simplemente confirma el cambio con calidez, por ejemplo: "¡Listo, actualicé tu viaje a Japón! Tu asesor ya tiene esta información" -- sin repetir el anuncio de escalamiento.

# Cada dato se pregunta UNA sola vez
Al final del último mensaje del cliente verás una nota interna del sistema (el cliente NO la ve) con los datos ya registrados y la lista de datos que todavía puedes preguntar, en orden. Esa nota manda sobre cualquier otra indicación:
- Primero registra lo que el cliente haya dicho en su último mensaje. Luego pregunta SOLO por el primer dato de esa lista que siga sin respuesta, y solo uno por mensaje.
- Un dato que NO aparece en la lista ya se tiene o ya se preguntó: NUNCA vuelvas a preguntarlo ni lo reformules de otra manera, aunque el cliente haya dicho "no sé", haya cambiado de tema o no haya respondido.
- Si el cliente responde "no sé" o evade la pregunta, no insistas ni comentes que falta ese dato: sigue con el siguiente de la lista.
- Mientras no haya un destino (o una promo) registrado, NO preguntes por fecha, personas ni presupuesto: ayúdale a elegir con el catálogo, sin presionar. Si solo está averiguando, responde sus dudas con gusto.
- Cuando la nota diga que ya no queda nada por preguntar, escala en ese mismo turno.
- Nunca menciones la nota ni su contenido al cliente.

# Si el cliente escribe con nombre de usuario (sin número visible)
El sistema te indica más abajo si este cliente escribe con un nombre
de usuario de WhatsApp (no tiene número visible para ti). SOLO si aplica,
la nota interna incluirá "su número de WhatsApp" en la lista de datos por
preguntar:
- La primera vez, pídelo con calidez: "¿Por favor escríbeme tu número de
WhatsApp para que el asesor te escriba directamente?" (no lo copies
literal, adáptalo).
- Si el cliente responde con un número: regístralo con
registrar_datos_viaje en telefono_alternativo.
- Si la nota indica que es la segunda y última vez (el cliente respondió
"a este mismo número", "por aquí" o no lo dio): aclárale "Por el momento
no tengo acceso para verlo, ¿podrías escribírmelo por aquí, por favor?"
(no lo copies literal, adáptalo).
- Si tampoco lo comparte, NO vuelvas a insistir.

# Cuándo escalar (llama a escalar_a_asesor)
- La nota interna indica que ya no queda nada por preguntar: escala con
tipo "datos_completos", aunque falten datos que el cliente no supo o no
quiso responder.
- El cliente pregunta precios en cualquier forma: tipo "pregunta_precio".
- El cliente pide hablar con una persona: tipo "pide_humano".
- El cliente quiere reservar o muestra clara intención de compra: tipo
"intencion_compra".

En estos tres últimos casos escala de inmediato, sin hacer antes las
preguntas pendientes.

Si la herramienta te responde que antes debes preguntar algo, haz esa
pregunta con naturalidad en un mensaje corto y NO menciones al asesor en
ese mensaje.

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
despedirte con la frase exacta, no para seguir la conversación.

IMPORTANTE: escalar significa LLAMAR a la herramienta escalar_a_asesor. Nunca anuncies que un asesor contactará al cliente sin haber llamado la herramienta en ese mismo turno. Decirlo sin llamarla deja al cliente abandonado.

CHEQUEO OBLIGATORIO antes de responder: si tu respuesta menciona que un asesor va a contactar al cliente, DEBES haber llamado escalar_a_asesor en ese mismo turno -- sin excepción. Si no llamaste la herramienta, no puedes mencionar al asesor en tu respuesta bajo ninguna circunstancia.

Además, antes de escalar, registra con registrar_datos_viaje TODOS los datos nuevos que el cliente mencionó en su último mensaje, incluso si vienen varios juntos en la misma frase (ej. "diciembre y somos 4" contiene fecha Y número de personas -- registra ambos, no solo uno)."""
TOOLS = [
    {
        "name": "registrar_datos_viaje",
        "description": "Registra o actualiza los datos del viaje que el cliente ha mencionado. Llámala cada vez que el cliente aporte información nueva o corrija algo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destino": {
                    "type": "string",
                    "description": "Cualquier lugar que el cliente haya nombrado, TAL CUAL lo dijo y al nivel que lo dijo: país ('México'), departamento o región ('Nariño'), ciudad, isla o parque. También una promo ('Promo San Andrés') o un tipo de viaje que el cliente pida como tal: un crucero ('Crucero', 'Crucero por el Caribe') o un tour ('Tour por Europa'). No lo cambies por algo más específico ni esperes a que lo precise. Si el cliente no ha nombrado ningún lugar ni promo, deja este campo vacío.",
                },
                "fecha_viaje": {
                    "type": "string",
                    "description": "Fecha del viaje TAL COMO el cliente la mencionó, en sus propias palabras (ej. 'mediados de diciembre', 'la primera semana de enero', 'del 10 al 15 de marzo', 'en 2 meses'). NO conviertas a fecha exacta ni inventes un rango de días -- copia la expresión del cliente casi literal, solo limpiándola un poco si hace falta.",
                },
                "num_personas": {"type": "integer", "description": "Número de viajeros"},
                "presupuesto": {"type": "string", "description": "Presupuesto mencionado, en COP"},
                "telefono_alternativo": {
                    "type": "string",
                    "description": "Número de WhatsApp alternativo que el cliente compartió, SOLO relevante para clientes que escriben con un nombre de usuario (sin número visible). Guárdalo tal como lo escribió el cliente.",
                },
                "notas": {"type": "string", "description": "Contexto útil: ocasión especial, preferencias, ciudad de origen, preguntas del cliente que debe resolver el asesor, etc."},
            },
        },
    },
    {
        "name": "escalar_a_asesor",
        "description": "Escala la conversación a un asesor humano. Úsala cuando la nota interna indique que ya no queda nada por preguntar, cuando pregunten precio, cuando pidan hablar con una persona o cuando quieran reservar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string", "description": "Motivo del escalamiento en pocas palabras"},
                "tipo": {
                    "type": "string",
                    "enum": ["datos_completos", "pregunta_precio", "pide_humano", "intencion_compra"],
                    "description": "Razón principal del escalamiento. datos_completos: ya no queda nada por preguntar. Los otros tres escalan de inmediato, sin hacer las preguntas pendientes.",
                },
            },
            "required": ["motivo", "tipo"],
        },
    },
]

class FalloAPI(Exception):
    """La API de Anthropic no respondió tras los reintentos del SDK. La
    tarea de Celery la captura y reintenta más tarde."""


DESPEDIDA = "Un asesor de Lusso te contactará pronto para hablar de los detalles."
# Cuando el cliente pregunta el precio, el cierre explica por qué no se da
# un valor en el chat. Texto fijo: cámbialo aquí si quieres otro tono.
EXPLICACION_PRECIO = (
    "El valor depende de varios factores, como las fechas, el número de "
    "personas y el tipo de alojamiento."
)
MENSAJE_RESPALDO = "¡Dame un momentico! Ya te respondo 🙏"
SALUDO = "¡Hola! 👋 Soy el asistente virtual de Lusso Travel."

# Si el bot le dice al cliente que un asesor lo va a contactar, el código
# garantiza que el escalamiento ocurra aunque Claude no llame la herramienta.
PROMESA_ASESOR = re.compile(r"asesor.{0,40}(contactar|escribir|comunicar)", re.IGNORECASE)

# Señales de que Claude "pensó en voz alta": el bot le habla AL cliente,
# nunca habla DE "el cliente" ni de notas, herramientas o errores.
PATRON_FUGA = re.compile(
    r"\[|nota interna|sistema|herramienta|escalar_a_asesor|registrar_datos|\btool\b|"
    r"instrucci[oó]n|\berror\b|me equivoqu|(mensaje|respuesta) anterior|"
    r"\b(el|al) cliente\b",
    re.IGNORECASE,
)
RESPUESTA_FIJA_CON_ASESOR = "¡Con gusto! Tu asesor te escribirá directamente para ayudarte con eso 😊"

# Intenciones que escalan de inmediato. Se detectan en el mensaje del
# cliente por código: si aparecen, el lead escala aunque Claude no lo haga.
INTENCIONES_URGENTES = [
    ("pregunta_precio", "preguntó por el precio", re.compile(
        r"cu[aá]nto (vale|cuesta|sale|cobran|ser[ií]a|me sale|es el)|"
        r"qu[eé] (precio|valor|costo)|\bprecios?\b|\bvalor(es)?\b|\bcostos?\b|\btarifas?\b|"
        r"cotizaci[oó]n|cot[ií]za|a c[oó]mo|cu[aá]nto.{0,30}(viaje|paquete|plan|tour|promo)",
        re.IGNORECASE)),
    ("pide_humano", "pidió hablar con una persona", re.compile(
        r"(hablar|comunicar|contactar).{0,25}(asesor|persona|humano|alguien|agente)|"
        r"\b(un|una|el|la) (asesora?|persona real|humano|agente)\b|ll[aá]m(en|ame|enme)\b",
        re.IGNORECASE)),
    ("intencion_compra", "quiere reservar o comprar", re.compile(
        r"(quiero|deseo|quisiera|necesito|vamos a) (reservar|comprar|pagar|separar|apartar)|"
        r"c[oó]mo (reservo|compro|separo|aparto)|listo para (reservar|pagar)",
        re.IGNORECASE)),
]


def _intencion_urgente(texto):
    """(tipo, descripción) si el mensaje del cliente pide precio, una
    persona o reservar; None si no."""
    for tipo, descripcion, patron in INTENCIONES_URGENTES:
        if patron.search(texto or ""):
            return tipo, descripcion
    return None


def _cierre_precio(texto):
    """Arma el mensaje de cierre cuando el cliente preguntó el precio: lo
    cálido que haya escrito Claude + la explicación fija + la despedida.
    Se descartan sus frases sobre precios o el asesor para no repetir."""
    frases = re.split(r"(?<=[.!?])\s+", _quitar_preguntas(texto))
    utiles = [
        f for f in frases
        if re.search(r"[a-záéíóúñ]", f, re.IGNORECASE)
        and not re.search(r"precio|valor|cost|tarifa|cotiza|asesor", f, re.IGNORECASE)
    ]
    return " ".join(utiles + [EXPLICACION_PRECIO, DESPEDIDA])


def _quitar_preguntas(texto):
    """Devuelve el texto hasta antes de la frase que contiene la primera
    pregunta (se descarta esa frase completa y todo lo que sigue)."""
    idx = texto.find("¿")
    if idx == -1:
        idx = texto.find("?")
    if idx == -1:
        return texto.strip()
    cortes = [p + len(sep) for sep in (". ", "! ", "? ", "\n") if (p := texto.rfind(sep, 0, idx)) != -1]
    # Si no hay una frase anterior completa, se corta justo en la pregunta.
    inicio = max(cortes) if cortes else idx
    return texto[:inicio].strip(" ,:;")


# ── Cada dato se pregunta UNA sola vez (lo controla el código) ──────────────
# Orden en que se preguntan los datos una vez hay destino. El destino no
# tiene tope: sin destino el bot ofrece el catálogo y no avanza.
ORDEN_PREGUNTAS = ["fecha_viaje", "num_personas", "presupuesto"]
CAMPO_TELEFONO = "telefono_alternativo"  # solo clientes con username
# El teléfono admite un segundo intento (la aclaración "no puedo ver tu
# número"), porque sin él el asesor no puede contactar al cliente.
MAX_INTENTOS = {CAMPO_TELEFONO: 2}
ETIQUETAS = {
    "destino": "el destino",
    "fecha_viaje": "la fecha del viaje",
    "num_personas": "el número de personas",
    "presupuesto": "el presupuesto",
    CAMPO_TELEFONO: "su número de WhatsApp",
}
# Preguntas de reemplazo cuando hay que descartar el texto de Claude.
PREGUNTA_FIJA = {
    "destino": "¿Ya tienes algún destino en mente para tu viaje? 😊",
    "fecha_viaje": "¿Para qué fecha te gustaría viajar?",
    "num_personas": "¿Cuántas personas viajarían?",
    "presupuesto": "¿Tienes un presupuesto en mente para el viaje?",
    CAMPO_TELEFONO: "¿Me escribes tu número de WhatsApp para que el asesor te contacte?",
}
# Cómo reconocer, en el texto que el bot envió, qué dato preguntó.
PATRON_PREGUNTA = {
    "fecha_viaje": re.compile(r"cu[aá]ndo|fecha|\bmes\b|[eé]poca|temporada", re.IGNORECASE),
    "num_personas": re.compile(r"personas|viajer|acompa[ñn]|qui[eé]n|cu[aá]nt[oa]s (van|ir|son|ser|viaj)", re.IGNORECASE),
    "presupuesto": re.compile(r"presupuesto|invertir|gastar", re.IGNORECASE),
    CAMPO_TELEFONO: re.compile(r"n[uú]mero|whatsapp|celular|tel[eé]fono", re.IGNORECASE),
}
# Preguntas que NO son de datos (elegir destino/parque/categoría del catálogo).
PATRON_PREGUNTA_CATALOGO = re.compile(
    r"cu[aá]l|parque|cat[aá]logo|destino|opci[oó]n|conocer|prefier|tour|circuito|pa[ií]s|ciudad", re.IGNORECASE
)

# Únicos campos que Claude puede escribir en datos_viaje.
CAMPOS_REGISTRABLES = {"destino", "fecha_viaje", "num_personas", "presupuesto", CAMPO_TELEFONO, "notas"}


def _hechas(d, campo):
    """Cuántas veces se le ha preguntado ya este dato al cliente."""
    n = (d.get("preguntas_hechas") or {}).get(campo, 0)
    # Compatibilidad con leads creados con las banderas anteriores.
    if campo == "presupuesto" and d.get("presupuesto_preguntado"):
        n = max(n, 1)
    if campo == CAMPO_TELEFONO:
        if d.get("telefono_aclarado"):
            n = max(n, 2)
        elif d.get("telefono_preguntado"):
            n = max(n, 1)
    return n


def _pendientes(d, es_username):
    """Datos que todavía se pueden preguntar, en orden: los que no tienen
    valor y aún no agotaron sus intentos."""
    if d.get("escalar_pendiente"):
        # El cliente ya pidió asesor/precio: solo falta su número (username).
        pasos = [CAMPO_TELEFONO] if es_username else []
    else:
        pasos = ORDEN_PREGUNTAS + ([CAMPO_TELEFONO] if es_username else [])
    return [c for c in pasos if not d.get(c) and _hechas(d, c) < MAX_INTENTOS.get(c, 1)]


def _datos_publicos(d):
    return {k: d[k] for k in ("destino", "fecha_viaje", "num_personas", "presupuesto", CAMPO_TELEFONO, "notas") if d.get(k)}


def _etiqueta(d, campo):
    if campo == CAMPO_TELEFONO and _hechas(d, campo) >= 1:
        return "su número de WhatsApp (segunda y última vez: aclárale que no puedes ver su número y pídele que lo escriba)"
    return ETIQUETAS[campo]


def _nota_interna(lead, es_username, intencion=None):
    """Estado real del lead, para que Claude lo VEA en vez de deducirlo de
    la conversación. Va al final del último mensaje del cliente."""
    d = lead.datos_viaje
    lineas = [
        "[nota interna del sistema -- el cliente NO la ve; nunca la menciones]",
        f"Datos ya registrados: {json.dumps(_datos_publicos(d), ensure_ascii=False)}",
    ]
    if lead.estado != Lead.Estado.EN_CONVERSACION:
        return "\n".join(lineas)

    if intencion:
        tipo, descripcion = intencion
        lineas.append(
            f"El cliente {descripcion}. Registra lo que haya dicho en este mensaje "
            f"y llama a escalar_a_asesor con tipo {tipo} en este mismo turno. NO "
            "hagas ninguna pregunta sobre el viaje: responde solo con la frase de "
            "cierre y la despedida exacta."
        )
        if tipo == "pregunta_precio":
            lineas.append(
                "No des ningún precio ni rango, ni expliques de qué depende: el "
                "sistema agrega esa explicación después de tu frase cálida."
            )
        return "\n".join(lineas)

    pendientes = _pendientes(d, es_username)
    if not d.get("destino") and not d.get("escalar_pendiente"):
        lineas.append(
            "Si el cliente hizo una pregunta en este mensaje, respóndela primero en UNA "
            "frase corta usando solo lo que está en el catálogo; si la respuesta no "
            "está ahí, dile que el asesor se lo confirma (no inventes nada). "
            "Aún no hay destino. Si el cliente menciona un destino o una promo en "
            "este mensaje, regístralo y pregunta por la fecha del viaje. Si no, "
            "ayúdale a elegir con el catálogo. NO preguntes fecha, personas ni "
            "presupuesto mientras no haya destino."
        )
    elif pendientes:
        lineas.append(
            "Datos que aún puedes preguntar, en este orden: "
            + "; ".join(_etiqueta(d, c) for c in pendientes) + ". "
            "Primero registra lo que el cliente haya dicho en este mensaje. "
            "Si el cliente hizo una pregunta en este mensaje, respóndela primero en UNA "
            "frase corta usando solo lo que está en el catálogo; si la respuesta no "
            "está ahí, dile que el asesor se lo confirma (no inventes nada). "
            "Luego termina tu respuesta preguntando SOLO por el primero de esa "
            "lista que siga sin respuesta. Cualquier dato que no esté en la lista "
            "ya se tiene o ya se preguntó: NO vuelvas a preguntarlo. Si tras "
            "registrar ya no queda ninguno, escala con tipo datos_completos."
        )
    else:
        lineas.append(
            "Ya no queda nada por preguntar. Registra lo que el cliente haya "
            "dicho en este mensaje y llama a escalar_a_asesor con tipo "
            "datos_completos en este mismo turno. No hagas más preguntas."
        )
    return "\n".join(lineas)


def _faltantes_para_escalar(d, es_username, urgente):
    """Qué falta preguntar antes de aceptar un escalamiento. Los
    escalamientos urgentes (precio, pide persona, quiere reservar) solo
    esperan el número del cliente con username."""
    pendientes = _pendientes(d, es_username)
    if urgente:
        return [c for c in pendientes if c == CAMPO_TELEFONO]
    sin_destino = not d.get("destino") and not d.get("escalar_pendiente")
    return (["destino"] if sin_destino else []) + pendientes


def _marcar_preguntas_hechas(lead, texto, es_username):
    """Tras enviar la respuesta, anota qué dato(s) preguntó el bot para no
    volver a preguntarlos nunca. No depende de que Claude lleve la cuenta."""
    d = lead.datos_viaje
    if not (d.get("destino") or d.get("escalar_pendiente")):
        return
    pendientes = _pendientes(d, es_username)
    preguntas = " ".join(re.findall(r"[^.!?¿]*\?", texto or ""))
    if not pendientes or not preguntas:
        return

    preguntados = [c for c in pendientes if PATRON_PREGUNTA[c].search(preguntas)]
    if not preguntados and not PATRON_PREGUNTA_CATALOGO.search(preguntas):
        # Hizo una pregunta que no reconocemos: asumimos que fue la que tocaba.
        preguntados = [pendientes[0]]
    if not preguntados:
        return

    hechas = dict(d.get("preguntas_hechas") or {})
    for campo in preguntados:
        hechas[campo] = _hechas(d, campo) + 1
    lead.datos_viaje = {**d, "preguntas_hechas": hechas}
    lead.save(update_fields=["datos_viaje", "updated_at"])
    logger.info("Lead %s: preguntas ya hechas -> %s", lead.nombre, hechas)


def _asegurar_pregunta_correcta(lead, texto, es_username):
    """Con destino ya registrado, la única pregunta válida es la del dato
    que toca. Si Claude preguntó otra cosa (afinar el destino, ofrecer el
    catálogo, etc.), se conserva lo que dijo antes de preguntar y la
    pregunta se cambia por la fija. No depende del prompt."""
    d = lead.datos_viaje
    if not (d.get("destino") or d.get("escalar_pendiente")):
        return texto
    pendientes = _pendientes(d, es_username)
    preguntas = " ".join(re.findall(r"[^.!?¿]*\?", texto or ""))
    if not pendientes or not preguntas:
        return texto
    if any(PATRON_PREGUNTA[c].search(preguntas) for c in pendientes):
        return texto

    antes = _quitar_preguntas(texto)
    logger.warning("Lead %s: pregunta fuera de guion, se reemplaza: %r", lead.nombre, texto[len(antes):].strip())
    return f"{antes} {PREGUNTA_FIJA[pendientes[0]]}".strip()


def _limpiar_param(valor):
    """Meta rechaza parámetros de plantilla con saltos de línea, tabs o
    muchos espacios seguidos (error 132018)."""
    texto = re.sub(r"[\n\t\r]+", " ", str(valor))
    texto = re.sub(r" {2,}", " ", texto).strip()
    return texto[:1000] or "No especifica"


def _system_prompt():
    """System prompt con la fecha de hoy inyectada (cambia una vez al día,
    así el caché se invalida solo a medianoche)."""
    return SYSTEM_PROMPT_TEMPLATE.format(fecha_hoy=date.today().isoformat())


def _marcar_ultimo_bloque_cacheable(messages):
    """
    Deja UN solo cache_control en los mensajes: en el último bloque del
    último mensaje. Antes se acumulaba uno por vuelta del bucle y a la 5ª
    la API devolvía 400 (máximo 4 marcadores). Con uno solo el cache sigue
    funcionando: la API busca coincidencias de prefijo hacia atrás.
    """
    if not messages:
        return messages

    # Quitar marcadores previos (solo dicts; los bloques del SDK no los tienen)
    for msg in messages:
        if isinstance(msg["content"], list):
            msg["content"] = [
                {k: v for k, v in b.items() if k != "cache_control"} if isinstance(b, dict) else b
                for b in msg["content"]
            ]

    ultimo = messages[-1]
    contenido = ultimo["content"]

    if isinstance(contenido, str):
        ultimo["content"] = [
            {"type": "text", "text": contenido, "cache_control": {"type": "ephemeral"}}
        ]
    else:
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
def responder_mensaje(lead_id, avisar_fallo=True):
    """Responde al último mensaje del lead.

    Si la API de Anthropic falla, lanza FalloAPI para que la tarea de Celery
    reintente más tarde. `avisar_fallo` controla si antes se le manda al
    cliente el mensaje de "dame un momentico" (solo en el primer intento).
    """
    from .whatsapp import enviar_texto

    lead = Lead.objects.get(id=lead_id)
    # Reintentos inmediatos (segundos). Los reintentos largos los hace Celery.
    client = Anthropic(max_retries=2, timeout=30)

    historial = _construir_historial(lead)
    if not historial:
        return

    es_username = not lead.telefono.isdigit()
    activo = lead.estado == Lead.Estado.EN_CONVERSACION
    es_primer_mensaje = not lead.mensajes.filter(rol=Mensaje.Rol.BOT).exists()

    escalado = False
    respuesta_texto = ""
    forzado_ya = False
    fallo_api = False

    # El marcador de cache va en el último bloque REAL de la conversación.
    # La nota interna se agrega DESPUÉS del marcador: cambia en cada turno y,
    # si quedara dentro del prefijo cacheado, el turno siguiente no acertaría
    # el cache.
    intencion = None
    if activo and historial[-1]["role"] == "user":
        intencion = _intencion_urgente(historial[-1]["content"][-1]["text"])

    messages = _marcar_ultimo_bloque_cacheable(historial)
    if messages[-1]["role"] == "user":
        messages[-1]["content"].append({"type": "text", "text": _nota_interna(lead, es_username, intencion)})

    for vuelta in range(5):
        if vuelta:
            messages = _marcar_ultimo_bloque_cacheable(messages)

        # Mientras no haya destino, el primer paso del turno es SIEMPRE
        # registrar lo que el cliente dijo (aunque sea nada). Así "México" o
        # "Nariño" quedan como destino antes de que Claude redacte, y no
        # depende de que decida registrarlo.
        d_actual = lead.datos_viaje
        forzar_registro = (
            vuelta == 0 and activo
            and not d_actual.get("destino") and not d_actual.get("escalar_pendiente")
        )
        extra = {"tool_choice": {"type": "tool", "name": "registrar_datos_viaje"}} if forzar_registro else {}

        try:
            response = client.messages.create(
                model=MODELO,
                max_tokens=1024,
                system=[
                    # Marcador propio: el prompt se sirve de cache aunque cambie
                    # tool_choice entre una llamada y otra.
                    {"type": "text", "text": _system_prompt(), "cache_control": {"type": "ephemeral"}},
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
                **extra,
            )
        except anthropic.APIError:
            logger.exception("Lead %s: fallo de la API de Anthropic", lead_id)
            fallo_api = True
            break

        _log_uso_cache(lead_id, response)

        if response.stop_reason == "max_tokens":
            logger.warning("Lead %s: respuesta truncada por max_tokens", lead_id)

        texto_turno = "".join(b.text for b in response.content if b.type == "text").strip()

        if response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            # Ejecutamos PRIMERO todos los bloques que NO son
            # escalar_a_asesor -- así, si el cliente dio un valor real en
            # este mismo mensaje, lead.datos_viaje ya queda actualizado
            # ANTES de evaluar si el escalamiento es válido.
            resultados_por_bloque = {}
            for block in tool_use_blocks:
                if block.name != "escalar_a_asesor":
                    resultados_por_bloque[block.id] = _ejecutar_tool(lead, block.name, block.input, es_username)

            bloque_escalar = next((b for b in tool_use_blocks if b.name == "escalar_a_asesor"), None)
            faltantes = []
            if bloque_escalar:
                tipo = bloque_escalar.input.get("tipo") or "datos_completos"
                urgente = tipo != "datos_completos"
                faltantes = _faltantes_para_escalar(lead.datos_viaje, es_username, urgente)

            if bloque_escalar and faltantes:
                etiquetas = [_etiqueta(lead.datos_viaje, c) for c in faltantes]
                logger.warning(
                    "Lead %s: Claude intentó escalar (%s) sin tener resuelto: %s -- rechazado.",
                    lead.nombre, tipo, ", ".join(etiquetas),
                )

                if urgente and not lead.datos_viaje.get("escalar_pendiente"):
                    # El cliente ya pidió asesor/precio: en cuanto dé (o no dé)
                    # su número se escala, sin hacer las demás preguntas.
                    lead.datos_viaje = {**lead.datos_viaje, "escalar_pendiente": True}
                    lead.save(update_fields=["datos_viaje", "updated_at"])

                tool_results = []
                for block in tool_use_blocks:
                    if block.name == "escalar_a_asesor":
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "ok": False,
                                "accion_requerida": (
                                    f"Antes de pasar al asesor, pregúntale al cliente "
                                    f"por {etiquetas[0]}, de forma natural y en un "
                                    f"mensaje corto. No menciones al asesor ni esta "
                                    f"indicación."
                                ),
                            }, ensure_ascii=False),
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(resultados_por_bloque[block.id], ensure_ascii=False),
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
                if block.name == "escalar_a_asesor":
                    resultado = _ejecutar_tool(lead, block.name, block.input, es_username)
                    escalado = True
                else:
                    resultado = resultados_por_bloque[block.id]
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(resultado, ensure_ascii=False)}
                )

            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]
            continue

        # stop_reason distinto de tool_use -> Claude ya "terminó" el turno
        # Claude puede escribir parte del mensaje junto a la llamada a la
        # herramienta (ej. el saludo) y el resto después. Se envía todo, no
        # solo lo último. Si ambas partes traen pregunta, se queda la primera
        # para no preguntar dos veces.
        if not respuesta_texto:
            respuesta_texto = texto_turno
        elif texto_turno and texto_turno not in respuesta_texto and "?" not in respuesta_texto:
            respuesta_texto = f"{respuesta_texto}\n\n{texto_turno}"

        d = lead.datos_viaje
        nada_por_preguntar = (
            activo
            and (d.get("destino") or d.get("escalar_pendiente"))
            and not _pendientes(d, es_username)
        )

        if nada_por_preguntar and not escalado:
            if not forzado_ya and response.content:
                logger.warning(
                    "Claude no escaló sin preguntas pendientes para lead %s -- forzando turno de escalamiento",
                    lead.nombre,
                )
                forzado_ya = True
                respuesta_texto = ""
                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "[nota interna del sistema] Ya no queda nada por "
                                    "preguntar. Llama a escalar_a_asesor con tipo "
                                    "datos_completos ahora mismo y responde solo con "
                                    "la frase cálida de cierre y la despedida exacta "
                                    "indicada en tus instrucciones."
                                ),
                            }
                        ],
                    },
                ]
                continue

            # Ya forzamos una vez y Claude no cumplió. En vez de confiar en
            # un segundo intento, ejecutamos el escalamiento nosotros mismos
            # en código y sobreescribimos cualquier texto que haya generado.
            logger.error(
                "Lead %s: Claude no llamó a escalar_a_asesor tras ser "
                "forzado -- ejecutando el escalamiento directamente en "
                "código.", lead.nombre,
            )
            _ejecutar_tool(lead, "escalar_a_asesor", {"motivo": "forzado por sistema (Claude no cumplió)"}, es_username)
            escalado = True
            respuesta_texto = DESPEDIDA

        break
    else:
        logger.warning("Tope de iteraciones de tool use alcanzado para lead %s", lead_id)

    if fallo_api and not escalado:
        # No se guarda como mensaje del BOT: si quedara en el historial, el
        # reintento vería un turno del asistente al final de la conversación.
        if avisar_fallo:
            enviar_texto(lead.telefono, MENSAJE_RESPALDO)
            Mensaje.objects.create(
                lead=lead, rol=Mensaje.Rol.SISTEMA,
                contenido=f"La IA no respondió. Se envió al cliente: «{MENSAJE_RESPALDO}». Reintentando en unos minutos.",
            )
        raise FalloAPI(f"Anthropic no respondió para el lead {lead_id}")

    # URGENTE: el cliente preguntó precio, pidió una persona o quiere
    # reservar. Si Claude no escaló, lo hace el código.
    if intencion and not escalado:
        d = lead.datos_viaje
        antes = _quitar_preguntas(respuesta_texto)
        if _faltantes_para_escalar(d, es_username, urgente=True):
            # Cliente con username: falta su número para que el asesor lo contacte.
            if not d.get("escalar_pendiente"):
                lead.datos_viaje = {**d, "escalar_pendiente": True}
                lead.save(update_fields=["datos_viaje", "updated_at"])
            if not PATRON_PREGUNTA[CAMPO_TELEFONO].search(respuesta_texto):
                respuesta_texto = f"{antes} {PREGUNTA_FIJA[CAMPO_TELEFONO]}".strip()
        else:
            logger.error("Lead %s: el cliente %s y Claude no escaló -- escalando en código", lead.nombre, intencion[1])
            _ejecutar_tool(lead, "escalar_a_asesor", {"motivo": f"el cliente {intencion[1]}"}, es_username)
            escalado = True
            respuesta_texto = f"{antes} {DESPEDIDA}".strip()

    if escalado and intencion and intencion[0] == "pregunta_precio":
        respuesta_texto = _cierre_precio(respuesta_texto)

    if escalado and not respuesta_texto:
        respuesta_texto = DESPEDIDA

    # FILTRO: si Claude narró su razonamiento o mencionó algo interno, ese
    # texto no se envía. Se reemplaza por un mensaje fijo según lo que toque.
    if respuesta_texto and PATRON_FUGA.search(respuesta_texto):
        logger.error("Lead %s: texto interno en la respuesta, se reemplaza: %r", lead.nombre, respuesta_texto)
        d = lead.datos_viaje
        if escalado:
            respuesta_texto = DESPEDIDA
        elif not activo:
            respuesta_texto = RESPUESTA_FIJA_CON_ASESOR
        elif not d.get("destino") and not d.get("escalar_pendiente"):
            respuesta_texto = PREGUNTA_FIJA["destino"]
        else:
            pendientes = _pendientes(d, es_username)
            respuesta_texto = PREGUNTA_FIJA[pendientes[0]] if pendientes else DESPEDIDA

    # PREGUNTA: con destino registrado, solo se pregunta el dato que toca.
    if activo and not escalado and respuesta_texto:
        respuesta_texto = _asegurar_pregunta_correcta(lead, respuesta_texto, es_username)

    # BANDERA: si el bot le prometió un asesor al cliente sin haber escalado,
    # la promesa se cumple en código.
    if activo and not escalado and PROMESA_ASESOR.search(respuesta_texto):
        logger.error("Lead %s: el bot prometió asesor sin escalar -- escalando en código", lead.nombre)
        _ejecutar_tool(lead, "escalar_a_asesor", {"motivo": "promesa de asesor sin llamar la herramienta"}, es_username)
        escalado = True

    # Anotamos qué dato acaba de preguntar el bot, para no repetirlo nunca.
    if activo and not escalado:
        _marcar_preguntas_hechas(lead, respuesta_texto, es_username)

    # SALUDO: el primer mensaje del bot siempre se presenta, lo escriba
    # Claude o no.
    if respuesta_texto and es_primer_mensaje and not re.search(r"asistente|lusso travel", respuesta_texto, re.IGNORECASE):
        sin_hola = re.sub(r"^[\s¡]*(hola|buen[oa]s( d[ií]as| tardes| noches)?)[\s,.!👋😊]*", "", respuesta_texto, flags=re.IGNORECASE)
        respuesta_texto = f"{SALUDO}\n\n{sin_hola or respuesta_texto}"

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


def _ejecutar_tool(lead, nombre, inputs, es_username=False):
    if nombre == "registrar_datos_viaje":
        # Claude solo puede escribir los campos del viaje; el control de qué
        # ya se preguntó lo lleva el código.
        datos = {k: v for k, v in inputs.items() if v and k in CAMPOS_REGISTRABLES}
        lead.datos_viaje = {**lead.datos_viaje, **datos}
        lead.save(update_fields=["datos_viaje", "updated_at"])
        logger.info("Datos de viaje actualizados para %s: %s", lead.nombre, datos)
        d = lead.datos_viaje
        if d.get("destino") or d.get("escalar_pendiente"):
            pendientes = [_etiqueta(d, c) for c in _pendientes(d, es_username)]
        else:
            pendientes = ["el destino"]
        return {
            "ok": True,
            "datos_actuales": _datos_publicos(d),
            "aun_puedes_preguntar_en_orden": pendientes,
        }

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
                    _limpiar_param(p) for p in [
                        lead.nombre, link_whatsapp, destino,
                        fecha_viaje, no_especifica, num_personas,
                        presupuesto, notas,
                    ]
                ],
            )
            logger.info("Notificación de WhatsApp enviada al asesor para lead %s", lead.nombre)
        except Exception:
            logger.exception("No se pudo notificar al asesor sobre el lead %s", lead.nombre)
            # Que el fallo quede visible en el chat del portal, no solo en logs.
            Mensaje.objects.create(
                lead=lead, rol=Mensaje.Rol.SISTEMA,
                contenido="⚠️ NO se pudo enviar la notificación al asesor. Revisar este lead manualmente.",
            )