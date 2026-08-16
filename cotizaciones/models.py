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
    descripcion_destino_imagen = models.URLField(
        blank=True,
        help_text="URL del PNG transparente generado automáticamente a partir de descripcion_destino.",
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
    bienvenida_descripcion_imagen = models.URLField(
        blank=True,
        help_text="URL del PNG transparente generado automáticamente a partir de bienvenida_descripcion.",
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
    viaje_sonado_intro_texto = models.TextField(
        blank=True,
        help_text="Párrafo 'Al llegar a [destino]...'. Se pre-llena desde DestinoContenido "
                   "si existe una entrada con el mismo nombre de destino.",
    )
    viaje_sonado_intro_imagen = models.URLField(
        blank=True,
        help_text="URL del PNG transparente generado automáticamente a partir de viaje_sonado_intro_texto.",
    )
    viaje_sonado_texto1 = models.TextField(
        blank=True,
        help_text="Párrafo bajo 'Disfrutas cada instante'. Se pre-llena desde DestinoContenido.",
    )
    viaje_sonado_texto1_imagen = models.URLField(
        blank=True,
        help_text="URL del PNG transparente generado automáticamente a partir de viaje_sonado_texto1.",
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

class DestinoContenido(models.Model):
    """
    Catálogo de contenido reutilizable por destino. Se carga una vez
    (ej. "Brasil", "Coveñas") y sirve para PRE-LLENAR una cotización
    nueva a ese destino. Una vez copiado a la cotización, es totalmente
    independiente: editar la cotización NO modifica este catálogo.
    """
    nombre = models.CharField(
        max_length=150, unique=True,
        help_text="Nombre exacto del destino, ej: 'Coveñas', 'Brasil'. "
                   "Se usa para buscar coincidencia al crear una cotización nueva.",
    )

    # --- Página "Imagina despertar aquí" ---
    descripcion_destino = models.TextField(blank=True)
    imagen_destino = models.URLField(blank=True)
    imagen_destino_secundaria = models.URLField(blank=True)

    # --- Página "Bienvenidos a [destino]" ---
    bienvenida_descripcion = models.TextField(blank=True)
    imagen_bienvenida = models.URLField(blank=True)

    # --- Página "Tu viaje soñado" ---
    imagen_viaje_sonado = models.URLField(blank=True)
    viaje_sonado_intro_texto = models.TextField(blank=True)
    viaje_sonado_texto1 = models.TextField(blank=True)

    # --- Página "El arte de vivir" ---
    imagen_arte_vivir_1 = models.URLField(blank=True)
    imagen_arte_vivir_2 = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "destinos_contenido"
        ordering = ["nombre"]
        verbose_name = "Contenido de destino"
        verbose_name_plural = "Contenidos de destino"

    def __str__(self):
        return self.nombre


class HotelPartner(models.Model):
    """
    Catálogo reutilizable de hoteles. Se llena una sola vez por hotel
    y se reutiliza en todas las cotizaciones que lo incluyan.
    """
    destino = models.ForeignKey(
        DestinoContenido, on_delete=models.PROTECT, null=True, blank=True,
        related_name="hoteles",
        help_text="Destino al que pertenece este hotel. Se usa para filtrar "
                   "qué hoteles mostrar al elegir un destino en el formulario.",
    )
    nombre = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)
    direccion = models.TextField(blank=True)
    descripcion = models.TextField(blank=True)
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
    plan de alimentación, datos importantes y precios), no lo que es
    fijo del hotel en sí.
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

    datos_importantes = models.JSONField(
        default=list, blank=True,
        help_text="Datos importantes de la estadía, en viñetas (ej. horario de "
                   "restaurante, check-in, check-out). Se carga por cotización, "
                   "puede variar según el hotel/cliente. Ej: "
                   "['Horario restaurante: 6:00 A.M a 10:00 P.M', 'Check-in: 3:00 PM']",
    )
    precios = models.JSONField(
        default=list, blank=True,
        help_text="Opciones de precio para este hotel, en viñetas de texto libre "
                   "(reemplaza mostrar el precio en la página de inversión cuando "
                   "hay varios hoteles a elegir). Ej: "
                   "['$2.500.000 x persona - Estándar - Alimentación: DESAYUNOS', "
                   "'$2.650.000 x persona - Vista al mar']",
    )

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

