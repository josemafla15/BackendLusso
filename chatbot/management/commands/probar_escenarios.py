"""
Corre conversaciones guionadas contra el bot VARIAS veces y revisa reglas
que nunca deberían romperse. Sirve para medir con datos qué tan seguido falla.

Uso:
    python manage.py probar_escenarios                 # cada escenario 5 veces
    python manage.py probar_escenarios --veces 20
    python manage.py probar_escenarios --solo precio   # solo escenarios cuyo nombre contenga "precio"

Ubicación: <tu_app>/management/commands/probar_escenarios.py

Usa la API real de Anthropic (Haiku): 6 escenarios x 5 repeticiones
cuesta del orden de centavos de dólar. Córrelo contra la BD LOCAL, nunca producción.
"""
import os
import re
from collections import defaultdict
from unittest.mock import patch

from django.core.management.base import BaseCommand

from leads.models import Lead
from chatbot.models import Mensaje
from chatbot.claude_service import responder_mensaje

PATCH_ENVIAR_TEXTO = "chatbot.whatsapp.enviar_texto"
PATCH_ENVIAR_PLANTILLA = "chatbot.whatsapp.enviar_plantilla"

# ─────────────────────────────────────────────────────────────────────────────

ESCENARIOS = [
    {
        "nombre": "flujo_completo",
        "username": False,
        "mensajes": ["hola", "quiero ir a Cartagena", "en diciembre, somos 4", "unos 8 millones"],
        "debe_escalar": True,
    },
    {
        "nombre": "todo_en_un_mensaje",
        "username": False,
        "mensajes": ["Hola! quiero ir a San Andrés en enero con mi esposa, tenemos 5 millones", "gracias"],
        "debe_escalar": True,
    },
    {
        "nombre": "evade_presupuesto",
        "username": False,
        "mensajes": ["buenas", "Japón", "en marzo, vamos 2", "no sé todavía"],
        "debe_escalar": True,
    },
    {
        "nombre": "pregunta_precio",
        "username": False,
        "mensajes": ["hola", "cuánto cuesta ir a Cancún?"],
        "debe_escalar": True,
    },
    {
        "nombre": "pide_humano",
        "username": False,
        "mensajes": ["hola", "prefiero hablar con una persona"],
        "debe_escalar": True,
    },
    {
        "nombre": "username_da_numero",
        "username": True,
        "mensajes": ["hola", "quiero ir a Punta Cana", "en junio somos 3", "unos 10 millones", "3001234567"],
        "debe_escalar": True,
    },
]

# Reglas que se revisan en CADA mensaje del bot
PROMESA_ASESOR = re.compile(r"asesor.{0,40}(contactar|escribir|comunicar)", re.IGNORECASE)
FUGA_INTERNA = re.compile(
    r"\[sistema|herramienta|escalar_a_asesor|registrar_datos|\btool\b|instrucci[oó]n|"
    r"\berror\b|me equivoqu|debo pregunt|voy a (registrar|escalar)",
    re.IGNORECASE,
)
PRECIO = re.compile(r"(\$\s?\d)|(\d[\d.,]*\s*(pesos|mil|millones|cop|usd|d[oó]lares))", re.IGNORECASE)
VOSEO = re.compile(r"\b(ten[eé]s|quer[eé]s|pod[eé]s|sos|vos)\b", re.IGNORECASE)


class Command(BaseCommand):
    help = "Corre escenarios guionados contra el bot y cuenta violaciones de reglas"

    def add_arguments(self, parser):
        parser.add_argument("--veces", type=int, default=5)
        parser.add_argument("--solo", type=str, default="")
        parser.add_argument("--verbose", action="store_true", help="Imprime cada conversación")

    def handle(self, *args, **opts):
        escenarios = [e for e in ESCENARIOS if opts["solo"] in e["nombre"]]
        fallos = defaultdict(list)          # nombre_escenario -> [descripción]
        corridas = 0

        for esc in escenarios:
            for i in range(opts["veces"]):
                corridas += 1
                problemas, transcripcion = self._correr(esc)
                if problemas:
                    fallos[esc["nombre"]].append((i + 1, problemas, transcripcion))
                marca = self.style.ERROR("✗") if problemas else self.style.SUCCESS("✓")
                self.stdout.write(f"{marca} {esc['nombre']} #{i + 1}" + (f"  → {', '.join(problemas)}" if problemas else ""))
                if opts["verbose"] or problemas:
                    for linea in transcripcion:
                        self.stdout.write(f"      {linea}")

        self.stdout.write("\n" + "─" * 60)
        total_fallos = sum(len(v) for v in fallos.values())
        self.stdout.write(f"Corridas: {corridas} | Con problemas: {total_fallos}")
        for nombre in [e["nombre"] for e in escenarios]:
            n = len(fallos.get(nombre, []))
            estilo = self.style.ERROR if n else self.style.SUCCESS
            self.stdout.write(estilo(f"  {nombre}: {n}/{opts['veces']} con problemas"))

    def _correr(self, esc):
        telefono = f"prueba_{esc['nombre']}" if esc["username"] else "570000000999"
        Lead.objects.filter(telefono=telefono).delete()
        lead = Lead.objects.create(nombre=f"Test {esc['nombre']}", telefono=telefono)

        enviados = []
        plantillas = []
        problemas = []
        transcripcion = []

        def fake_texto(tel, texto):
            enviados.append(texto)

        def fake_plantilla(tel, nombre, params):
            plantillas.append(params)
            for p in params:
                if re.search(r"[\n\t]| {5,}", str(p)):
                    problemas.append("plantilla_param_invalido")

        with patch(PATCH_ENVIAR_TEXTO, fake_texto), \
             patch(PATCH_ENVIAR_PLANTILLA, fake_plantilla), \
             patch.dict(os.environ, {"ASESOR_WHATSAPP": "570000000001"}):

            for msg in esc["mensajes"]:
                Mensaje.objects.create(lead=lead, rol=Mensaje.Rol.CLIENTE, contenido=msg)
                transcripcion.append(f"👤 {msg}")
                enviados.clear()

                try:
                    responder_mensaje(lead.id)
                except Exception as e:
                    problemas.append(f"excepcion:{type(e).__name__}")
                    transcripcion.append(f"💥 {type(e).__name__}: {e}")
                    break

                lead.refresh_from_db()
                if not enviados:
                    problemas.append("sin_respuesta")
                    transcripcion.append("🤖 (nada)")

                for t in enviados:
                    transcripcion.append(f"🤖 {t}")
                    if FUGA_INTERNA.search(t):
                        problemas.append("fuga_interna")
                    if PRECIO.search(t):
                        problemas.append("posible_precio")
                    if VOSEO.search(t):
                        problemas.append("voseo")
                    if PROMESA_ASESOR.search(t) and lead.estado == Lead.Estado.EN_CONVERSACION:
                        problemas.append("prometio_asesor_sin_escalar")

        escalo = lead.estado != Lead.Estado.EN_CONVERSACION
        if esc["debe_escalar"] and not escalo:
            problemas.append("no_escalo")
        if len(plantillas) > 1:
            problemas.append(f"plantilla_duplicada x{len(plantillas)}")

        transcripcion.append(f"   [estado final={lead.estado} | datos={lead.datos_viaje}]")
        Lead.objects.filter(id=lead.id).delete()
        return sorted(set(problemas)), transcripcion