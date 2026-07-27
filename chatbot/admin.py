from django.contrib import admin

from .models import Mensaje


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ("lead", "rol", "contenido", "created_at")
    list_filter = ("rol",)
    search_fields = ("contenido", "lead__nombre")
    readonly_fields = ("id", "created_at")