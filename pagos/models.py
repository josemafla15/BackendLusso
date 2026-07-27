import secrets
import uuid

from django.db import models

from cotizaciones.models import Cotizacion


def generar_token():
    return secrets.token_urlsafe(32)


class Pago(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        DECLINADO = "declinado", "Declinado"
        ANULADO = "anulado", "Anulado"
        REEMBOLSADO = "reembolsado", "Reembolsado"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.PROTECT, related_name="pagos")
    token = models.TextField(unique=True, default=generar_token)
    monto = models.DecimalField(max_digits=12, decimal_places=0)  # congelado al crear
    metodo_pago = models.TextField(null=True, blank=True)  # CARD, NEQUI, PSE...
    estado = models.TextField(choices=Estado.choices, default=Estado.PENDIENTE)
    wompi_transaction_id = models.TextField(null=True, blank=True, unique=True)
    referencia = models.TextField(unique=True, null=True, blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)
    expira_en = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pagos"
        ordering = ["-created_at"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"{self.monto} COP — {self.get_estado_display()}"