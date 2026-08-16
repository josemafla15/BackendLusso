(function esperarDjangoJQuery(intentos) {
  if (window.django && window.django.jQuery) {
    inicializarPrefillDestino(window.django.jQuery);
  } else if (intentos > 0) {
    setTimeout(function () {
      esperarDjangoJQuery(intentos - 1);
    }, 50);
  } else {
    console.error("prefill_destino.js: django.jQuery nunca apareció, abortando.");
  }
})(40);

function inicializarPrefillDestino($) {
  $(function () {
    const $destino = $("#id_destino");
    if (!$destino.length) return;

    // Solo tiene sentido en el formulario de creación (add), no al editar
    // una cotización que ya tiene sus propios textos.
    const esCreacion = window.location.pathname.includes("/add/");
    if (!esCreacion) return;

    const mapaCampos = {
      descripcion_destino: "#id_descripcion_destino",
      imagen_destino: "#id_imagen_destino",
      imagen_destino_secundaria: "#id_imagen_destino_secundaria",
      bienvenida_descripcion: "#id_bienvenida_descripcion",
      imagen_bienvenida: "#id_imagen_bienvenida",
      imagen_viaje_sonado: "#id_imagen_viaje_sonado",
      viaje_sonado_intro_texto: "#id_viaje_sonado_intro_texto",
      viaje_sonado_texto1: "#id_viaje_sonado_texto1",
      imagen_arte_vivir_1: "#id_imagen_arte_vivir_1",
      imagen_arte_vivir_2: "#id_imagen_arte_vivir_2",
    };

    $destino.on("blur", function () {
      const nombre = $(this).val().trim();
      if (!nombre) return;

      $.get("/cotizaciones/admin/cotizaciones/buscar-destino/", { nombre: nombre }, function (resp) {
        if (!resp.encontrado) return;

        let algoSeLleno = false;
        Object.entries(mapaCampos).forEach(([campo, selector]) => {
          const $campo = $(selector);
          const valorActual = $campo.val();
          const valorCatalogo = resp.datos[campo];
          if (!valorActual && valorCatalogo) {
            $campo.val(valorCatalogo);
            algoSeLleno = true;
          }
        });

        if (algoSeLleno) {
          $("<div class='help' style='color:#2952a3;font-weight:600;'>"
            + "✓ Textos e imágenes cargados desde el catálogo de '" + nombre + "'."
            + "</div>").insertAfter($destino.closest(".form-row"));
        }
      });
    });
  });
}