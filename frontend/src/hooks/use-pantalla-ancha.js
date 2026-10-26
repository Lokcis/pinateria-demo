import { useEffect, useState } from "react";

/** Desde este ancho (el `xl` de Tailwind) la app usa menu lateral; por debajo, barra inferior de celular. */
const CONSULTA_ANCHA = "(min-width: 1280px)";

/**
 * Indica si la pantalla es ancha (computador o tablet horizontal) o angosta (celular).
 *
 * Sin `matchMedia` (por ejemplo, en las pruebas) se considera ancha.
 *
 * @returns {boolean} True si la pantalla es ancha.
 */
export function usePantallaAncha() {
  const [ancha, setAncha] = useState(() =>
    typeof window.matchMedia === "function" ? window.matchMedia(CONSULTA_ANCHA).matches : true
  );

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const consulta = window.matchMedia(CONSULTA_ANCHA);
    const alCambiar = () => setAncha(consulta.matches);
    alCambiar();
    consulta.addEventListener("change", alCambiar);
    return () => consulta.removeEventListener("change", alCambiar);
  }, []);

  return ancha;
}
