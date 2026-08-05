import secrets
import uuid

from django.db import models

from leads.models import Lead


def generar_referencia():
    return f"LUSSO-{secrets.token_hex(4).upper()}"


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
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="pagos")

    cliente_nombre = models.TextField()
    cliente_contacto = models.TextField()
    destino = models.TextField(default="")
    descripcion = models.TextField(blank=True, default="")

    monto = models.DecimalField(max_digits=12, decimal_places=0)
    metodo_pago = models.TextField(null=True, blank=True)

    token = models.TextField(unique=True, default=generar_token)
    referencia = models.TextField(unique=True, default=generar_referencia)

    estado = models.TextField(choices=Estado.choices, default=Estado.PENDIENTE)
    wompi_transaction_id = models.TextField(null=True, blank=True, unique=True)
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
        return f"{self.cliente_nombre} — {self.destino}"