from django.urls import path
from . import views

urlpatterns = [
    path("<str:token>/", views.resolver_pago, name="resolver_pago"),
]