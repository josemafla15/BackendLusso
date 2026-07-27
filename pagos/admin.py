from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("cotizacion", "monto", "estado", "wompi_transaction_id", "created_at")
    list_filter = ("estado",)
    search_fields = ("wompi_transaction_id", "referencia", "cotizacion__lead__nombre")
    readonly_fields = ("id", "token", "created_at", "updated_at")