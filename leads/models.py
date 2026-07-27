import uuid

from django.conf import settings
from django.db import models


class Lead(models.Model):
    class Origen(models.TextChoices):
        POPUP = "popup", "Popup de descuento"
        CONTACTO = "contacto", "Formulario de contacto"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Estado(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        EN_CONVERSACION = "en_conversacion", "En conversación"
        CALIFICADO = "calificado", "Calificado"
        COTIZADO = "cotizado", "Cotizado"
        GANADO = "ganado", "Ganado"
        PERDIDO = "perdido", "Perdido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.TextField()
    contacto = models.TextField()
    destino_interes = models.TextField(null=True, blank=True)
    mensaje = models.TextField(null=True, blank=True)
    origen = models.TextField(choices=Origen.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    telefono = models.TextField(null=True, blank=True)
    estado = models.TextField(choices=Estado.choices, default=Estado.NUEVO)
    datos_viaje = models.JSONField(default=dict, blank=True)
    bot_activo = models.BooleanField(default=True)
    bot_pausado_hasta = models.DateTimeField(null=True, blank=True)
    ultima_notif_asesor = models.DateTimeField(null=True, blank=True)
    asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leads"
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        constraints = [
            models.UniqueConstraint(
                fields=["telefono"],
                condition=models.Q(origen="whatsapp"),
                name="unique_telefono_whatsapp",
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_origen_display()})"