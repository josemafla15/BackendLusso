from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from chatbot.models import Mensaje
from cotizaciones.models import Cotizacion, DestinoContenido, HotelPartner
from cotizaciones.storage import subir_archivo_temporal
from leads.models import Lead
from pagos.models import Pago

from rest_framework.decorators import action

from .serializers import (
    CotizacionSerializer,
    DestinoContenidoSerializer,
    HotelPartnerSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    PagoSerializer,
    UserSerializer,
)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — username + password → access + refresh."""
    throttle_classes = [LoginThrottle]


@api_view(["GET"])
def me(request):
    """GET /api/me/ — el usuario autenticado."""
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@parser_classes([MultiPartParser])
def subir_imagen(request):
    """
    POST /api/upload-imagen/ — multipart, campo "archivo" + opcional "carpeta".
    El backend sube el archivo a Supabase Storage y devuelve la URL pública.
    Alternativa a subir directo desde el front con la publishable key.
    """
    archivo = request.FILES.get("archivo")
    if not archivo:
        return Response({"error": "Falta el archivo (campo 'archivo')."}, status=400)

    carpeta = request.data.get("carpeta", "uploads")
    url = subir_archivo_temporal(archivo, carpeta=carpeta)
    return Response({"url": url})


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().select_related("asesor").order_by("-updated_at")
    filterset_fields = ["origen", "estado", "asesor"]
    search_fields = ["nombre", "contacto", "telefono", "destino_interes"]
    ordering_fields = ["created_at", "updated_at"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        return LeadDetailSerializer


class DestinoContenidoViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura -- el catálogo se administra desde Django admin."""
    queryset = DestinoContenido.objects.all().order_by("nombre")
    serializer_class = DestinoContenidoSerializer
    search_fields = ["nombre"]
    http_method_names = ["get", "head", "options"]


class HotelPartnerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Solo lectura desde este front -- el catálogo de hoteles se administra
    desde Django admin. Filtrable por destino:
    GET /api/hoteles/?destino=<id>
    """
    queryset = HotelPartner.objects.filter(activo=True).select_related("destino")
    serializer_class = HotelPartnerSerializer
    filterset_fields = ["destino", "ciudad"]
    search_fields = ["nombre", "ciudad"]
    http_method_names = ["get", "head", "options"]


class CotizacionViewSet(viewsets.ModelViewSet):
    queryset = Cotizacion.objects.all().select_related("lead", "asesor").prefetch_related(
        "hoteles", "vuelos"
    ).order_by("-created_at")
    serializer_class = CotizacionSerializer
    filterset_fields = ["estado", "lead", "asesor"]
    search_fields = ["destino", "lead__nombre"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        """
        Además de estado/lead/asesor (filterset_fields) y search (search_fields),
        soporta filtrado por rango de fechas sobre updated_at:
        GET /api/cotizaciones/?fecha_desde=2026-08-01&fecha_hasta=2026-08-31
        Ambos parámetros son opcionales e independientes entre sí.
        """
        qs = super().get_queryset()
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")
        if fecha_desde:
            qs = qs.filter(updated_at__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(updated_at__date__lte=fecha_hasta)
        return qs

    def perform_create(self, serializer):
        serializer.save(asesor=self.request.user)

    @action(detail=True, methods=["post"], url_path="generar-pdf")
    def generar_pdf(self, request, pk=None):
        """
        POST /api/cotizaciones/<id>/generar-pdf/
        Body: {"nombre_archivo": "Cotizacion_Brasil_JuanPerez"}

        Encola la generación del PDF en Celery y responde de inmediato.
        El front debe hacer polling a GET /api/cotizaciones/<id>/ y
        esperar a que pdf_url deje de estar vacío.
        """
        from cotizaciones.tasks import generar_pdf_cotizacion_task

        cotizacion = self.get_object()
        nombre_archivo = request.data.get("nombre_archivo", "").strip()

        if not nombre_archivo:
            return Response({"detail": "Falta 'nombre_archivo'."}, status=400)

        # Se limpia antes de encolar, para que el polling del front
        # detecte de forma confiable cuándo terminó (incluso si es una
        # regeneración y el pdf_url anterior tenía el mismo valor).
        cotizacion.pdf_url = ""
        cotizacion.save(update_fields=["pdf_url"])

        generar_pdf_cotizacion_task.delay(str(cotizacion.id), nombre_archivo)

        return Response({"detail": "Generación de PDF encolada."}, status=202)

class PagoViewSet(viewsets.ModelViewSet):
    """El asesor puede crear pagos desde el dashboard (GET/POST).
    No se editan ni borran: el estado lo actualiza únicamente el webhook de Wompi."""
    queryset = Pago.objects.all().select_related("lead").order_by("-created_at")
    serializer_class = PagoSerializer
    filterset_fields = ["estado", "metodo_pago", "lead"]
    search_fields = ["referencia", "wompi_transaction_id", "cliente_nombre", "descripcion"]
    http_method_names = ["get", "post", "head", "options"]