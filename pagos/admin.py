from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("cliente_nombre", "destino", "monto", "estado", "metodo_pago", "created_at")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("cliente_nombre", "cliente_contacto", "referencia", "wompi_transaction_id")
    readonly_fields = ("id", "token", "referencia", "created_at", "updated_at")