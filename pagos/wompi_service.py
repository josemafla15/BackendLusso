import hashlib
import os

from .models import Pago


def crear_pago(cliente_nombre, cliente_contacto, destino, monto, lead=None):
    """Crea un registro de Pago listo para generar su link."""
    descripcion = f"{cliente_nombre} — {destino}"
    pago = Pago.objects.create(
        lead=lead,
        cliente_nombre=cliente_nombre,
        cliente_contacto=cliente_contacto,
        descripcion=descripcion,
        monto=monto,
    )
    return pago


def calcular_firma_integridad(pago):
    """Firma de integridad que exige el widget de Wompi.
    Fórmula oficial: SHA256(referencia + monto_en_centavos + moneda + secreto)
    """
    monto_centavos = int(pago.monto) * 100
    secreto = os.environ["WOMPI_INTEGRITY_SECRET"]
    cadena = f"{pago.referencia}{monto_centavos}COP{secreto}"
    return hashlib.sha256(cadena.encode()).hexdigest()


def datos_widget(pago):
    """Todo lo que el frontend necesita para mostrar el widget de Wompi."""
    return {
        "public_key": os.environ["WOMPI_PUBLIC_KEY"],
        "currency": "COP",
        "amount_in_cents": int(pago.monto) * 100,
        "reference": pago.referencia,
        "signature_integrity": calcular_firma_integridad(pago),
        "redirect_url": f"{os.environ.get('SITE_URL', '')}/pago/{pago.token}/confirmacion",
    }