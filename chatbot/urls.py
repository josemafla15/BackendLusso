from django.urls import path

from . import views

urlpatterns = [
    path("meta/", views.webhook_meta, name="webhook_meta"),
]