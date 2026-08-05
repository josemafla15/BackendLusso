from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("webhooks/", include("chatbot.urls")),
    path("webhooks/", include("pagos.urls_webhook")),
    path("pago/", include("pagos.urls")),
    path("api/", include("api.urls")),
]