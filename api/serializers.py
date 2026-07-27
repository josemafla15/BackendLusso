from django.contrib.auth.models import User
from rest_framework import serializers

from chatbot.models import Mensaje
from cotizaciones.models import Cotizacion
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
            "destino_interes", "mensaje", "datos_viaje", "asesor", "bot_activo",
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
            "bot_activo", "bot_pausado_hasta",
            "asesor", "asesor_id", "mensajes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "origen", "created_at", "updated_at"]


class CotizacionSerializer(serializers.ModelSerializer):
    asesor = UserSerializer(read_only=True)
    lead_nombre = serializers.CharField(source="lead.nombre", read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            "id", "lead", "lead_nombre", "asesor", "destino",
            "fecha_inicio", "fecha_fin", "num_personas", "precio",
            "incluye", "no_incluye", "vigencia", "version", "estado",
            "pdf_url", "notas", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "asesor", "version", "pdf_url", "created_at", "updated_at"]


class PagoSerializer(serializers.ModelSerializer):
    cotizacion_destino = serializers.CharField(source="cotizacion.destino", read_only=True)
    lead_nombre = serializers.CharField(source="cotizacion.lead.nombre", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id", "cotizacion", "cotizacion_destino", "lead_nombre",
            "monto", "estado", "metodo_pago", "referencia",
            "wompi_transaction_id", "expira_en", "created_at", "updated_at",
        ]