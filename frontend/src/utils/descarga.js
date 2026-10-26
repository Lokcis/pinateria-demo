/**
 * Descarga un archivo en el navegador (por ejemplo, un CSV que abre Excel).
 *
 * @param {Blob} contenido - El archivo.
 * @param {string} nombre - Nombre con que se guarda.
 */
export function descargarArchivo(contenido, nombre) {
  const direccion = URL.createObjectURL(contenido);
  const enlace = document.createElement("a");
  enlace.href = direccion;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(direccion);
}
