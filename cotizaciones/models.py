import uuid

from django.conf import settings
from django.db import models

from leads.models import Lead


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        GENERADA = "generada", "Generada"
        ENVIADA = "enviada", "Enviada"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        VENCIDA = "vencida", "Vencida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="cotizaciones")
    asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cotizaciones",
    )
    destino = models.TextField()
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    num_personas = models.PositiveIntegerField(default=1)

    # --- Página "Imagina despertar aquí" ---
    descripcion_destino = models.TextField(
        blank=True,
        help_text="Párrafo descriptivo del destino para la página 'Imagina despertar aquí'.",
    )
    imagen_destino = models.URLField(
        blank=True,
        help_text="URL pública (Supabase Storage) de la foto principal del destino.",
    )
    imagen_destino_secundaria = models.URLField(
        blank=True,
        help_text="URL pública (Supabase Storage) de la segunda foto, horizontal, debajo de la descripción.",
    )

    # --- Página "Bienvenidos a [destino]" ---
    bienvenida_descripcion = models.TextField(
        blank=True,
        help_text="Párrafo descriptivo para la página 'Bienvenidos a [destino]'.",
    )
    imagen_bienvenida = models.URLField(
        blank=True,
        help_text="URL pública (Supabase Storage) de la foto grande de la página Bienvenidos.",
    )

    # --- Página "Tu viaje soñado" ---
    imagen_viaje_sonado = models.URLField(
        blank=True,
        help_text="URL pública (Supabase Storage) de la foto horizontal grande de esta página.",
    )

    # --- Página "El arte de vivir" (sin texto descriptivo, solo 2 fotos) ---
    imagen_arte_vivir_1 = models.URLField(blank=True)
    imagen_arte_vivir_2 = models.URLField(blank=True)

    # --- Precio ---
    # precio_total: opcional -- algunas cotizaciones no tienen un total
    # único (ej. cuando hay varios hoteles a elegir, cada uno con su propio
    # precio). En ese caso se usa precio_nota_total en su lugar.
    precio_total = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True
    )  # COP
    precio_por_persona = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True
    )  # COP
    precio_nota_total = models.TextField(
        blank=True,
        help_text="Mensaje alternativo cuando no hay un total único, ej: "
                   "'Según la elección del hotel y adicionales, consulta el total con tu asesor'",
    )

    incluye = models.JSONField(default=list, blank=True)
    no_incluye = models.JSONField(default=list, blank=True)
    vigencia = models.DateField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    estado = models.TextField(choices=Estado.choices, default=Estado.BORRADOR)
    pdf_url = models.TextField(null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cotizaciones"
        ordering = ["-created_at"]
        verbose_name = "Cotización"
        verbose_name_plural = "Cotizaciones"

    def __str__(self):
        return f"{self.destino} — {self.lead.nombre} (v{self.version})"


class HotelPartner(models.Model):
    """
    Catálogo reutilizable de hoteles. Se llena una sola vez por hotel
    y se reutiliza en todas las cotizaciones que lo incluyan.
    """
    nombre = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)
    direccion = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
    horario_restaurante = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hoteles_partner"
        ordering = ["nombre"]
        verbose_name = "Hotel (catálogo)"
        verbose_name_plural = "Hoteles (catálogo)"

    def __str__(self):
        return f"{self.nombre} — {self.ciudad}"


class HotelImagen(models.Model):
    """
    Fotos del hotel, guardadas en Supabase Storage (bucket público).
    Este modelo solo guarda la URL pública, no el binario.
    """
    hotel = models.ForeignKey(HotelPartner, on_delete=models.CASCADE, related_name="imagenes")
    url = models.URLField()
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "hoteles_imagenes"
        ordering = ["orden"]
        verbose_name = "Imagen de hotel"
        verbose_name_plural = "Imágenes de hotel"

    def __str__(self):
        return f"{self.hotel.nombre} — imagen {self.orden}"


class CotizacionHotel(models.Model):
    """
    Instancia de un hotel dentro de UNA cotización específica.
    Guarda lo que varía por cliente/viaje (noches, tipo de habitación,
    plan de alimentación), no lo que es fijo del hotel.
    """
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="hoteles")
    hotel = models.ForeignKey(
        HotelPartner, on_delete=models.PROTECT, null=True, blank=True,
        related_name="cotizaciones_hotel",
    )
    # Fallback para un hotel puntual que no vale la pena meter al catálogo
    nombre_libre = models.CharField(max_length=200, blank=True)

    noches = models.PositiveIntegerField()
    tipo_habitacion = models.CharField(max_length=150, blank=True)
    plan_alimentacion = models.CharField(max_length=150, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "cotizaciones_hoteles"
        ordering = ["orden"]
        verbose_name = "Hotel de cotización"
        verbose_name_plural = "Hoteles de cotización"

    def __str__(self):
        nombre = self.hotel.nombre if self.hotel else self.nombre_libre
        return f"{nombre} ({self.noches} noches) — {self.cotizacion}"

    @property
    def nombre_display(self):
        return self.hotel.nombre if self.hotel else self.nombre_libre


class PrecioItem(models.Model):
    """
    Línea de precio individual dentro de una cotización. Cubre los casos
    que un solo precio_total/precio_por_persona no alcanza a representar:
      - Adultos / Niño (2 líneas, cada una con su tarifa)
      - Tarifa sencilla / doble
      - Un precio por cada hotel disponible a elegir (con su nota de
        alimentación, tipo de habitación, forma de pago, etc.)

    Si una cotización NO tiene ningún PrecioItem, el template usa el
    esquema simple (precio_total / precio_por_persona). Si SÍ tiene,
    el template muestra la lista de líneas en su lugar.
    """
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="precios")
    etiqueta = models.CharField(
        max_length=150,
        help_text="Ej: 'Adultos', 'Niño', 'Tarifa sencilla', 'Estándar', 'Vista al mar'",
    )
    precio = models.DecimalField(max_digits=12, decimal_places=0)  # COP, por persona
    nota = models.CharField(
        max_length=150, blank=True,
        help_text="Ej: 'DESAYUNOS', 'PAGO DE CONTADO' -- se muestra debajo de la línea",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "cotizaciones_precios"
        ordering = ["orden"]
        verbose_name = "Línea de precio"
        verbose_name_plural = "Líneas de precio"

    def __str__(self):
        return f"{self.etiqueta}: ${self.precio:,.0f} — {self.cotizacion}"


class Vuelo(models.Model):
    class Tipo(models.TextChoices):
        IDA = "ida", "Ida"
        VUELTA = "vuelta", "Vuelta"

    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="vuelos")
    tipo = models.CharField(choices=Tipo.choices, max_length=10)
    fecha = models.DateField()
    origen = models.CharField(max_length=10)   # código aeropuerto, ej "PSO"
    destino = models.CharField(max_length=10)  # código aeropuerto, ej "MTR"
    hora_salida = models.TimeField()
    hora_llegada = models.TimeField()
    aerolinea = models.CharField(max_length=100)
    paradas = models.PositiveIntegerField(default=0)
    duracion = models.CharField(max_length=20, blank=True)  # ej "4h 40m"
    imagen = models.URLField(
        blank=True,
        help_text="URL pública (Supabase Storage) de la captura de pantalla del vuelo (Avianca, Google Flights, etc.)",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "cotizaciones_vuelos"
        ordering = ["orden"]
        verbose_name = "Vuelo"
        verbose_name_plural = "Vuelos"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.origen} → {self.destino} ({self.fecha})"