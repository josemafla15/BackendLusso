from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from chatbot.models import Mensaje
from cotizaciones.models import Cotizacion
from leads.models import Lead
from pagos.models import Pago

from .serializers import (
    CotizacionSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    PagoSerializer,
    UserSerializer,
)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — email/username + password → access + refresh."""
    throttle_classes = [LoginThrottle]


@api_view(["GET"])
def me(request):
    """GET /api/me/ — el usuario autenticado (para el frontend al cargar)."""
    return Response(UserSerializer(request.user).data)


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().select_related("asesor").order_by("-updated_at")
    filterset_fields = ["origen", "estado", "asesor"]
    search_fields = ["nombre", "contacto", "telefono", "destino_interes"]
    ordering_fields = ["created_at", "updated_at"]
    http_method_names = ["get", "patch", "head", "options"]  # sin crear ni borrar desde la API

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        return LeadDetailSerializer


class CotizacionViewSet(viewsets.ModelViewSet):
    queryset = Cotizacion.objects.all().select_related("lead", "asesor").order_by("-created_at")
    serializer_class = CotizacionSerializer
    filterset_fields = ["estado", "lead", "asesor"]
    search_fields = ["destino", "lead__nombre"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(asesor=self.request.user)


class PagoViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: los pagos los crea/actualiza el sistema (Wompi), no el dashboard."""
    queryset = Pago.objects.all().select_related("cotizacion", "cotizacion__lead").order_by("-created_at")
    serializer_class = PagoSerializer
    filterset_fields = ["estado", "metodo_pago"]
    search_fields = ["referencia", "wompi_transaction_id", "cotizacion__lead__nombre"]