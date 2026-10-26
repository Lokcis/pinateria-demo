/** Politica de datos de ejemplo, con la forma de `GET /clientes/politica` (`PoliticaOut`). */
export const POLITICA_PRUEBA = {
  version: "1.0",
  datos_completos: true,
  faltantes: [],
  aviso: "Tienda de Prueba (NIT 900) usará tus datos solo para identificarte y asociar tus compras.",
  texto_autorizacion: "He leído este aviso y autorizo el tratamiento de mis datos personales.",
  texto_promociones: "Además, autorizo que me envíen promociones y novedades de la tienda (opcional).",
  texto_autorizacion_empleado: "El cliente leyó o escuchó este aviso y autoriza el tratamiento de sus datos personales.",
  texto_promociones_empleado: "El cliente además autoriza que le envíen promociones y novedades de la tienda (opcional).",
  secciones: [
    { titulo: "1. Responsable del tratamiento", parrafos: ["Tienda de Prueba, NIT 900."], items: [] },
    { titulo: "7. Derechos del titular", parrafos: ["El titular tiene derecho a:"], items: ["Conocer sus datos.", "Suprimirlos."] },
  ],
};
