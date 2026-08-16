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

    def perform_create(self, serializer):
        serializer.save(asesor=self.request.user)


class PagoViewSet(viewsets.ModelViewSet):
    """El asesor puede crear pagos desde el dashboard (GET/POST).
    No se editan ni borran: el estado lo actualiza únicamente el webhook de Wompi."""
    queryset = Pago.objects.all().select_related("lead").order_by("-created_at")
    serializer_class = PagoSerializer
    filterset_fields = ["estado", "metodo_pago", "lead"]
    search_fields = ["referencia", "wompi_transaction_id", "cliente_nombre", "descripcion"]
    http_method_names = ["get", "post", "head", "options"]