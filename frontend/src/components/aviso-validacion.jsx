import { useEffect, useRef, useState } from "react";

/** Cuanto dura el aviso en pantalla si la persona no corrige el campo (ms). */
const DURACION_MS = 6000;

/**
 * Posicion fija del aviso: justo debajo del campo, alineado a su borde izquierdo y sin salirse de la pantalla.
 *
 * @param {HTMLElement} campo
 * @returns {{top: number, left: number, maxWidth: number}}
 */
function posicionDebajoDe(campo) {
  const caja = campo.getBoundingClientRect();
  const margen = 12;
  const left = Math.min(Math.max(caja.left, margen), Math.max(margen, window.innerWidth - 280 - margen));
  return { top: caja.bottom + 8, left, maxWidth: window.innerWidth - left - margen };
}

/**
 * Reemplaza el globo gris del navegador ("El valor debe ser superior o igual a 1") por un aviso con el estilo de la
 * aplicacion, para todos los formularios a la vez.
 *
 * Escucha el evento `invalid` (que el navegador dispara al enviar un formulario con un campo incorrecto), cancela el
 * globo nativo, enfoca el primer campo con error y muestra su mensaje (ya viene en el idioma del navegador). El aviso
 * se quita al escribir en el campo, al salir de el, con Escape o a los pocos segundos. Se monta una sola vez en la raiz.
 *
 * @returns {JSX.Element | null}
 */
export function AvisoValidacion() {
  const [aviso, setAviso] = useState(null); // { campo, mensaje, posicion }
  const campoActual = useRef(null);
  const yaMostrado = useRef(false);

  useEffect(() => {
    let temporizador = null;

    const quitar = () => {
      campoActual.current = null;
      clearTimeout(temporizador);
      setAviso(null);
    };

    // El navegador dispara `invalid` en cada campo incorrecto: solo se muestra el primero de cada envio.
    const alSerInvalido = (evento) => {
      evento.preventDefault();
      if (yaMostrado.current) return;
      yaMostrado.current = true;
      setTimeout(() => {
        yaMostrado.current = false;
      }, 0);
      const campo = evento.target;
      campoActual.current = campo;
      campo.focus?.({ preventScroll: true });
      campo.scrollIntoView?.({ block: "center", behavior: "smooth" });
      setAviso({ campo, mensaje: campo.validationMessage, posicion: posicionDebajoDe(campo) });
      clearTimeout(temporizador);
      temporizador = setTimeout(quitar, DURACION_MS);
    };

    const alCorregir = (evento) => {
      if (evento.target === campoActual.current) quitar();
    };
    const alPulsar = (evento) => {
      if (evento.key === "Escape") quitar();
    };
    const alMover = () => {
      if (campoActual.current) setAviso((actual) => actual && { ...actual, posicion: posicionDebajoDe(actual.campo) });
    };

    document.addEventListener("invalid", alSerInvalido, true);
    document.addEventListener("input", alCorregir, true);
    document.addEventListener("change", alCorregir, true);
    document.addEventListener("focusout", alCorregir, true);
    document.addEventListener("keydown", alPulsar, true);
    window.addEventListener("scroll", alMover, true);
    window.addEventListener("resize", alMover);
    return () => {
      clearTimeout(temporizador);
      document.removeEventListener("invalid", alSerInvalido, true);
      document.removeEventListener("input", alCorregir, true);
      document.removeEventListener("change", alCorregir, true);
      document.removeEventListener("focusout", alCorregir, true);
      document.removeEventListener("keydown", alPulsar, true);
      window.removeEventListener("scroll", alMover, true);
      window.removeEventListener("resize", alMover);
    };
  }, []);

  if (!aviso) return null;
  return (
    <div
      role="alert"
      style={{ position: "fixed", top: aviso.posicion.top, left: aviso.posicion.left, maxWidth: aviso.posicion.maxWidth }}
      className="sombra-dura z-[100] flex items-start gap-2.5 rounded-2xl border-2 border-tinta bg-white px-3.5 py-2.5 text-sm font-semibold text-tinta"
    >
      <span
        aria-hidden="true"
        className="mt-px grid h-5 w-5 shrink-0 place-items-center rounded-full bg-fucsia text-xs font-extrabold text-white"
      >
        !
      </span>
      <span>{aviso.mensaje}</span>
    </div>
  );
}
