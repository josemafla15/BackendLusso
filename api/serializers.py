from django.contrib.auth.models import User
from rest_framework import serializers

from chatbot.models import Mensaje
from cotizaciones.models import (
    Cotizacion, CotizacionHotel, DestinoContenido, HotelPartner, Vuelo,
)
from leads.models import Lead
from pagos.models import Pago


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class MensajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mensaje
        fields = ["id", "rol", "contenido", "created_at"]


class LeadListSerializer(serializers.ModelSerializer):
    """Versión ligera para la bandeja."""
    asesor = UserSerializer(read_only=True)
    ultimo_mensaje = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "nombre", "contacto", "telefono", "origen", "estado",
            "destino_interes", "mensaje", "datos_viaje", "asesor",
            "created_at", "updated_at", "ultimo_mensaje",
        ]

    def get_ultimo_mensaje(self, obj):
        m = obj.mensajes.exclude(rol=Mensaje.Rol.SISTEMA).order_by("-created_at").first()
        if not m:
            return None
        return {"contenido": m.contenido[:80], "rol": m.rol, "created_at": m.created_at}


class LeadDetailSerializer(serializers.ModelSerializer):
    """Versión completa para el detalle: incluye el historial."""
    asesor = UserSerializer(read_only=True)
    asesor_id = serializers.PrimaryKeyRelatedField(
        source="asesor", queryset=User.objects.all(),
        required=False, allow_null=True, write_only=True,
    )
    mensajes = MensajeSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "nombre", "contacto", "telefono", "origen", "estado",
            "mensaje", "destino_interes", "datos_viaje",
            "bot_pausado_hasta",
            "asesor", "asesor_id", "mensajes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "origen", "created_at", "updated_at"]

class DestinoContenidoSerializer(serializers.ModelSerializer):
    """
    Solo lectura -- el catálogo se carga/edita por el admin de Django,
    no desde el front de cotizaciones. Se usa para el prefill al elegir
    un destino en el formulario nuevo.
    """
    class Meta:
        model = DestinoContenido
        fields = [
            "id", "nombre",
            "descripcion_destino", "imagen_destino", "imagen_destino_secundaria",
            "bienvenida_descripcion", "imagen_bienvenida",
            "imagen_viaje_sonado", "viaje_sonado_intro_texto", "viaje_sonado_texto1",
            "imagen_arte_vivir_1", "imagen_arte_vivir_2",
        ]


class HotelPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelPartner
        fields = [
            "id", "destino", "nombre", "ciudad", "direccion", "descripcion",
            "activo", "imagen_1", "imagen_2", "imagen_3",
        ]

    def get_imagenes(self, obj):
        return list(obj.imagenes.order_by("orden").values_list("url", flat=True))


class CotizacionHotelSerializer(serializers.ModelSerializer):
    nombre_display = serializers.CharField(read_only=True)

    class Meta:
        model = CotizacionHotel
        fields = [
            "id", "hotel", "nombre_libre", "noches",
            "tipo_habitacion", "plan_alimentacion",
            "datos_importantes", "precios",
            "orden", "nombre_display",
        ]


class VueloSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Vuelo
        fields = ["id", "tipo", "tipo_display", "imagen", "orden"]


class CotizacionSerializer(serializers.ModelSerializer):
    asesor = UserSerializer(read_only=True)
    lead_nombre = serializers.SerializerMethodField()
    hoteles = CotizacionHotelSerializer(many=True, required=False)
    vuelos = VueloSerializer(many=True, required=False)

    CAMPOS_CATALOGO = [
        "descripcion_destino", "imagen_destino", "imagen_destino_secundaria",
        "bienvenida_descripcion", "imagen_bienvenida",
        "imagen_viaje_sonado", "viaje_sonado_intro_texto", "viaje_sonado_texto1",
        "imagen_arte_vivir_1", "imagen_arte_vivir_2",
    ]

    class Meta:
        model = Cotizacion
        fields = [
            "id", "lead", "lead_nombre", "asesor", "destino", "nombre_cliente",
            "fecha_inicio", "fecha_fin", "num_personas",
            "descripcion_destino", "imagen_destino", "imagen_destino_secundaria",
            "bienvenida_descripcion", "imagen_bienvenida",
            "imagen_viaje_sonado", "viaje_sonado_intro_texto", "viaje_sonado_intro_imagen",
            "viaje_sonado_texto1", "viaje_sonado_texto1_imagen",
            "imagen_arte_vivir_1", "imagen_arte_vivir_2",
            "precio_total", "precio_por_persona", "precio_nota_total", "inversion_lineas",
            "incluye", "no_incluye", "vigencia", "version", "estado",
            "pdf_url", "notas", "hoteles", "vuelos",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "asesor", "version", "pdf_url",
            "viaje_sonado_intro_imagen", "viaje_sonado_texto1_imagen",
            "created_at", "updated_at",
        ]

    def get_lead_nombre(self, obj):
        return obj.lead.nombre if obj.lead else None

    def create(self, validated_data):
        hoteles_data = validated_data.pop("hoteles", [])
        vuelos_data = validated_data.pop("vuelos", [])

        # Fallback: si el front no manda nombre_cliente, usar el del lead
        if not validated_data.get("nombre_cliente"):
            lead = validated_data.get("lead")
            if lead:
                validated_data["nombre_cliente"] = lead.nombre

        # Prefill automático desde el catálogo -- mismo comportamiento que
        # ya tenía el admin (prefill_destino.js), pero centralizado acá
        # para que también aplique al crear desde la API/front.
        destino_nombre = (validated_data.get("destino") or "").strip()
        if destino_nombre:
            catalogo = DestinoContenido.objects.filter(nombre__iexact=destino_nombre).first()
            if catalogo:
                for campo in self.CAMPOS_CATALOGO:
                    if not validated_data.get(campo):
                        valor_catalogo = getattr(catalogo, campo)
                        if valor_catalogo:
                            validated_data[campo] = valor_catalogo

        cotizacion = Cotizacion.objects.create(**validated_data)

        for hotel_data in hoteles_data:
            CotizacionHotel.objects.create(cotizacion=cotizacion, **hotel_data)

        for vuelo_data in vuelos_data:
            Vuelo.objects.create(cotizacion=cotizacion, **vuelo_data)

        return cotizacion

    def update(self, instance, validated_data):
        hoteles_data = validated_data.pop("hoteles", None)
        vuelos_data = validated_data.pop("vuelos", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if hoteles_data is not None:
            instance.hoteles.all().delete()
            for hotel_data in hoteles_data:
                CotizacionHotel.objects.create(cotizacion=instance, **hotel_data)

        if vuelos_data is not None:
            instance.vuelos.all().delete()
            for vuelo_data in vuelos_data:
                Vuelo.objects.create(cotizacion=instance, **vuelo_data)

        return instance


class PagoSerializer(serializers.ModelSerializer):
    lead_nombre = serializers.CharField(source="lead.nombre", read_only=True, default=None)
    link_pago = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            "id", "lead", "lead_nombre", "cliente_nombre", "cliente_contacto",
            "destino", "descripcion", "monto", "metodo_pago", "token", "referencia",
            "estado", "wompi_transaction_id", "link_pago", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "token", "referencia", "estado", "wompi_transaction_id",
            "created_at", "updated_at",
        ]

    def get_link_pago(self, obj):
        import os
        base = os.environ.get("SITE_URL", "")
        return f"{base}/pago/{obj.token}"