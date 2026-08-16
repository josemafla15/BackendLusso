from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register("leads", views.LeadViewSet)
router.register("cotizaciones", views.CotizacionViewSet)
router.register("pagos", views.PagoViewSet)
router.register("destinos", views.DestinoContenidoViewSet)
router.register("hoteles", views.HotelPartnerViewSet)


urlpatterns = [
    path("auth/login/", views.LoginView.as_view(), name="api_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api_refresh"),
    path("me/", views.me, name="api_me"),
    path("upload-imagen/", views.subir_imagen, name="api_upload_imagen"),
    path("", include(router.urls)),
]