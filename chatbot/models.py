import uuid

from django.db import models

from leads.models import Lead


class Mensaje(models.Model):
    class Rol(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        BOT = "bot", "Bot"
        ASESOR = "asesor", "Asesor"
        SISTEMA = "sistema", "Sistema"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="mensajes")
    rol = models.TextField(choices=Rol.choices)
    contenido = models.TextField()
    wa_message_id = models.TextField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mensajes"
        ordering = ["created_at"]
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"

    def __str__(self):
        return f"[{self.get_rol_display()}] {self.contenido[:50]}"