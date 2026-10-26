import { useEffect, useState } from "react";

/**
 * Indica si el navegador tiene conexion de red (RNF 6.2: avisar claramente si se pierde).
 *
 * @returns {boolean} `true` si hay conexion.
 */
export function useEnLinea() {
  const [enLinea, setEnLinea] = useState(() => navigator.onLine);

  useEffect(() => {
    const alConectar = () => setEnLinea(true);
    const alDesconectar = () => setEnLinea(false);
    window.addEventListener("online", alConectar);
    window.addEventListener("offline", alDesconectar);
    return () => {
      window.removeEventListener("online", alConectar);
      window.removeEventListener("offline", alDesconectar);
    };
  }, []);

  return enLinea;
}
