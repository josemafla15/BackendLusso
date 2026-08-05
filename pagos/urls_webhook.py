from django.urls import path
from . import webhooks

urlpatterns = [
    path("wompi/", webhooks.webhook_wompi, name="webhook_wompi"),
]