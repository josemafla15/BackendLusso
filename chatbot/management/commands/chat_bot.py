"""
Chatea con el bot de Lusso desde la terminal, sin usar WhatsApp.

Uso:
    python manage.py chat_bot              # cliente con número normal
    python manage.py chat_bot --username   # cliente con username (sin número visible)

Comandos dentro del chat:
    /datos   -> muestra datos_viaje y estado del lead
    /reset   -> borra la conversación y empieza de cero
    /salir   -> termina

Ubicación: chatbot/management/commands/chat_bot.py

No envía nada por WhatsApp: los textos y la plantilla del asesor se imprimen
aquí. Sí usa la API real de Haiku y la base de datos de tu .env (crea y borra
un lead de prueba).
"""
import json
import os
from unittest.mock import patch

from django.core.management.base import BaseCommand

from leads.models import Lead
from chatbot.models import Mensaje
from chatbot.claude_service import responder_mensaje

PATCH_ENVIAR_TEXTO = "chatbot.whatsapp.enviar_texto"
PATCH_ENVIAR_PLANTILLA = "chatbot.whatsapp.enviar_plantilla"

TEL_NUMERO = "570000000000"
TEL_USERNAME = "usuario_prueba"


class Command(BaseCommand):
    help = "Chatea con el bot desde la terminal (WhatsApp simulado)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", action="store_true",
            help="Simula un cliente que escribe con username (sin número visible)",
        )

    def _nuevo_lead(self, telefono):
        Lead.objects.filter(telefono=telefono).delete()
        # En producción el webhook deja el lead en EN_CONVERSACION; aquí lo
        # hacemos igual, porque el escalamiento depende de ese estado.
        # Si tu modelo Lead exige más campos, agrégalos aquí.
        return Lead.objects.create(
            nombre="Cliente Prueba", telefono=telefono,
            estado=Lead.Estado.EN_CONVERSACION,
        )

    def handle(self, *args, **opts):
        telefono = TEL_USERNAME if opts["username"] else TEL_NUMERO
        lead = self._nuevo_lead(telefono)
        enviados = []

        def fake_enviar_texto(tel, texto):
            enviados.append(texto)

        def fake_enviar_plantilla(tel, nombre, params):
            self.stdout.write(self.style.WARNING(f"\n📨 PLANTILLA AL ASESOR '{nombre}':"))
            for p in params:
                self.stdout.write(f"     • {p!r}")

        self.stdout.write(self.style.SUCCESS(
            f"Chat de prueba iniciado ({'username, sin número visible' if opts['username'] else 'número normal'}). "
            "Escribe /salir para terminar.\n"
        ))

        with patch(PATCH_ENVIAR_TEXTO, fake_enviar_texto), \
             patch(PATCH_ENVIAR_PLANTILLA, fake_enviar_plantilla), \
             patch.dict(os.environ, {"ASESOR_WHATSAPP": "570000000001"}):

            while True:
                try:
                    msg = input("👤 Tú: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if not msg:
                    continue
                if msg in ("/salir", "/q"):
                    break
                if msg == "/reset":
                    lead = self._nuevo_lead(telefono)
                    self.stdout.write(self.style.SUCCESS("— conversación reiniciada —\n"))
                    continue
                if msg == "/datos":
                    lead.refresh_from_db()
                    self.stdout.write(f"   estado={lead.estado}")
                    self.stdout.write(f"   datos={json.dumps(lead.datos_viaje, ensure_ascii=False, indent=2)}\n")
                    continue

                Mensaje.objects.create(lead=lead, rol=Mensaje.Rol.CLIENTE, contenido=msg)
                enviados.clear()

                try:
                    responder_mensaje(lead.id)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"💥 EXCEPCIÓN: {type(e).__name__}: {e}\n"))

                lead.refresh_from_db()
                if not enviados:
                    self.stdout.write(self.style.ERROR("🤖 (el bot no envió nada)"))
                for t in enviados:
                    self.stdout.write(f"🤖 Bot: {t}")
                self.stdout.write(self.style.HTTP_INFO(
                    f"   [estado={lead.estado} | datos={json.dumps(lead.datos_viaje, ensure_ascii=False)}]\n"
                ))

        Lead.objects.filter(id=lead.id).delete()
        self.stdout.write("Chat terminado. Lead de prueba borrado.")