from django.contrib import admin

from .models import Cotizacion, CotizacionHotel, DestinoContenido, HotelImagen, HotelPartner, Vuelo


class CotizacionHotelInline(admin.TabularInline):
    model = CotizacionHotel
    extra = 1
    fields = (
        "orden", "hotel", "nombre_libre", "noches", "tipo_habitacion",
        "plan_alimentacion", "datos_importantes", "precios",
    )
    ordering = ("orden",)


class VueloInline(admin.TabularInline):
    model = Vuelo
    extra = 1
    fields = ("orden", "tipo", "imagen")
    ordering = ("orden",)


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "destino", "lead", "asesor", "cantidad_lineas_inversion",
        "estado", "version", "created_at",
    )
    list_filter = ("estado", "asesor")
    search_fields = ("destino", "lead__nombre")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [CotizacionHotelInline, VueloInline]

    class Media:
        js = ("cotizaciones/admin/prefill_destino.js",)

    @admin.display(description="Líneas de inversión")
    def cantidad_lineas_inversion(self, obj):
        return len(obj.inversion_lineas)


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