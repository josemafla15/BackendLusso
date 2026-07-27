from django.contrib import admin

from .models import Cotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("destino", "lead", "asesor", "precio", "estado", "version", "created_at")
    list_filter = ("estado", "asesor")
    search_fields = ("destino", "lead__nombre")
    readonly_fields = ("id", "created_at", "updated_at")