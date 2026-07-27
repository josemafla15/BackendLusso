from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "contacto", "origen", "estado", "destino_interes", "asesor", "created_at")
    list_filter = ("origen", "estado", "asesor")
    search_fields = ("nombre", "contacto", "telefono", "destino_interes")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")