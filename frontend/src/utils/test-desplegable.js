import { waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

/**
 * Elige una opcion de un `Desplegable` en los tests (equivale a `selectOptions`
 * del select nativo): abre el menu del combobox y pulsa la opcion por su valor.
 * Reintenta mientras la opcion aun no exista (p. ej. si las opciones cargan por API).
 *
 * @param {HTMLElement} combobox - El boton del desplegable.
 * @param {string} valor - Valor de la opcion (el `value` del `<option>`).
 * @returns {Promise<void>}
 */
export async function elegirOpcion(combobox, valor) {
  const buscar = () => {
    const lista = document.getElementById(combobox.getAttribute("aria-controls"));
    const opcion = lista?.querySelector(`[role="option"][data-valor="${valor}"]`);
    if (!opcion) throw new Error(`No hay una opcion con valor ${valor}`);
    return opcion;
  };
  await userEvent.click(combobox);
  let opcion;
  await waitFor(() => {
    opcion = buscar();
  });
  await userEvent.click(opcion);
}
