import uuid

from django.conf import settings
from django.db import models

from leads.models import Lead


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        GENERADA = "generada", "Generada"
        ENVIADA = "enviada", "Enviada"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        VENCIDA = "vencida", "Vencida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="cotizaciones")
    asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cotizaciones",
    )
    destino = models.TextField()
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    num_personas = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=12, decimal_places=0)  # COP
    incluye = models.JSONField(default=list, blank=True)
    no_incluye = models.JSONField(default=list, blank=True)
    vigencia = models.DateField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    estado = models.TextField(choices=Estado.choices, default=Estado.BORRADOR)
    pdf_url = models.TextField(null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cotizaciones"
        ordering = ["-created_at"]
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"

    def __str__(self):
        return f"{self.destino} — {self.lead.nombre} (v{self.version})"