from django.contrib import admin

from .models import Cotizacion, CotizacionHotel, DestinoContenido, HotelImagen, HotelPartner, Vuelo


class CotizacionHotelInline(admin.TabularInline):
    model = CotizacionHotel
    extra = 1
    fields = ("orden", "hotel", "nombre_libre", "noches", "tipo_habitacion", "plan_alimentacion")
    ordering = ("orden",)


class VueloInline(admin.TabularInline):
    model = Vuelo
    extra = 1
    fields = (
        "orden", "tipo", "fecha", "origen", "destino",
        "hora_salida", "hora_llegada", "aerolinea", "paradas", "duracion",
    )
    ordering = ("orden",)


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "destino", "lead", "asesor", "precio_total", "precio_por_persona",
        "estado", "version", "created_at",
    )
    list_filter = ("estado", "asesor")
    search_fields = ("destino", "lead__nombre")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [CotizacionHotelInline, VueloInline]

    class Media:
        js = ("cotizaciones/admin/prefill_destino.js",)


class HotelImagenInline(admin.TabularInline):
    model = HotelImagen
    extra = 1
    fields = ("orden", "url")
    ordering = ("orden",)


@admin.register(HotelPartner)
class HotelPartnerAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "activo", "updated_at")
    list_filter = ("ciudad", "activo")
    search_fields = ("nombre", "ciudad")
    inlines = [HotelImagenInline]


@admin.register(DestinoContenido)
class DestinoContenidoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "updated_at")
    search_fields = ("nombre",)