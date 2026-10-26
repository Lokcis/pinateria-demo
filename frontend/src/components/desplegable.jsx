import { Children, isValidElement, useEffect, useId, useRef, useState } from "react";

/**
 * Extrae las opciones de los `<option>` hijos (misma sintaxis que un `<select>`).
 *
 * @param {React.ReactNode} hijos
 * @returns {Array<{valor: string, etiqueta: string, deshabilitada: boolean}>}
 */
function leerOpciones(hijos) {
  return Children.toArray(hijos)
    .filter((hijo) => isValidElement(hijo) && hijo.type === "option")
    .map((hijo) => ({
      valor: String(hijo.props.value ?? ""),
      etiqueta: Children.toArray(hijo.props.children).join(""),
      deshabilitada: Boolean(hijo.props.disabled),
    }));
}

/**
 * Lista desplegable con el estilo de la app; reemplaza al `<select>` nativo,
 * cuyo menu no se puede personalizar.
 *
 * Es un reemplazo directo: recibe `<option>` como hijos y llama a
 * `onChange({ target: { value } })`, igual que un select. Soporta teclado
 * (flechas, Inicio/Fin, Enter/Espacio, Escape) y `required` (validacion nativa
 * del formulario). Las clases de `className` van en el boton.
 *
 * @param {{
 *   value: string|number, onChange: (evento: {target: {value: string}}) => void,
 *   children: React.ReactNode, className?: string, required?: boolean, disabled?: boolean,
 *   id?: string, "aria-label"?: string
 * }} props
 * @returns {JSX.Element}
 */
export function Desplegable({ value, onChange, children, className = "", required, disabled, ...resto }) {
  const idLista = useId();
  const raiz = useRef(null);
  const [abierto, setAbierto] = useState(false);
  const [activa, setActiva] = useState(0);

  const opciones = leerOpciones(children);
  const valorActual = String(value ?? "");
  const seleccionada = opciones.find((opcion) => opcion.valor === valorActual);
  const esPlaceholder = !seleccionada || seleccionada.valor === "";
  const habilitadas = opciones.map((opcion, indice) => (opcion.deshabilitada ? -1 : indice)).filter((i) => i >= 0);

  useEffect(() => {
    if (!abierto) return undefined;
    const alPulsarFuera = (evento) => {
      if (raiz.current && !raiz.current.contains(evento.target)) setAbierto(false);
    };
    document.addEventListener("mousedown", alPulsarFuera);
    return () => document.removeEventListener("mousedown", alPulsarFuera);
  }, [abierto]);

  /**
   * Abre el menu dejando activa la opcion seleccionada (o la primera habilitada).
   *
   * @returns {void}
   */
  function abrir() {
    if (disabled) return;
    const indice = opciones.findIndex((opcion) => opcion.valor === valorActual && !opcion.deshabilitada);
    setActiva(indice >= 0 ? indice : (habilitadas[0] ?? 0));
    setAbierto(true);
  }

  /**
   * Elige una opcion, avisa al padre y cierra el menu.
   *
   * @param {number} indice
   * @returns {void}
   */
  function elegir(indice) {
    const opcion = opciones[indice];
    if (!opcion || opcion.deshabilitada) return;
    onChange({ target: { value: opcion.valor } });
    setAbierto(false);
  }

  /**
   * Mueve la opcion activa entre las habilitadas.
   *
   * @param {number} paso - +1 o -1.
   * @returns {void}
   */
  function mover(paso) {
    const posicion = habilitadas.indexOf(activa);
    const siguiente = habilitadas[Math.min(Math.max(posicion + paso, 0), habilitadas.length - 1)];
    if (siguiente !== undefined) setActiva(siguiente);
  }

  /**
   * Teclado del boton: abre con flechas/Enter/Espacio y navega el menu abierto.
   *
   * @param {React.KeyboardEvent} evento
   * @returns {void}
   */
  function alPulsarTecla(evento) {
    if (evento.key === "Escape") {
      if (abierto) {
        evento.stopPropagation();
        setAbierto(false);
      }
      return;
    }
    if (["ArrowDown", "ArrowUp", "Enter", " ", "Home", "End"].includes(evento.key)) evento.preventDefault();
    if (!abierto) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(evento.key)) abrir();
      return;
    }
    if (evento.key === "ArrowDown") mover(1);
    else if (evento.key === "ArrowUp") mover(-1);
    else if (evento.key === "Home") setActiva(habilitadas[0] ?? 0);
    else if (evento.key === "End") setActiva(habilitadas.at(-1) ?? 0);
    else if (evento.key === "Enter" || evento.key === " ") elegir(activa);
    else if (evento.key === "Tab") setAbierto(false);
  }

  return (
    <div ref={raiz} className="relative min-w-0">
      <button
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={abierto}
        aria-controls={abierto ? idLista : undefined}
        disabled={disabled}
        onClick={() => (abierto ? setAbierto(false) : abrir())}
        onKeyDown={alPulsarTecla}
        className={`flex w-full cursor-pointer items-center justify-between gap-2 text-left transition hover:border-tinta focus-visible:border-fucsia focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-fucsia/20 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
        {...resto}
      >
        <span className={`truncate ${esPlaceholder ? "text-tinta/45" : ""}`}>{seleccionada?.etiqueta || " "}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={`h-4 w-4 shrink-0 text-tinta/60 transition-transform ${abierto ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {required && (
        <input
          tabIndex={-1}
          aria-hidden="true"
          required
          value={valorActual}
          onChange={() => {}}
          className="pointer-events-none absolute bottom-0 left-0 h-px w-full opacity-0"
        />
      )}

      {abierto && (
        <ul
          id={idLista}
          role="listbox"
          onClick={(evento) => evento.preventDefault()} // dentro de un <label>, evita que el clic reabra el boton
          className="absolute left-0 z-40 mt-1.5 max-h-60 w-max min-w-full max-w-[20rem] animate-pop overflow-auto rounded-2xl border border-tinta/10 bg-white p-1.5 shadow-xl shadow-tinta/15"
        >
          {opciones.map((opcion, indice) => {
            if (opcion.deshabilitada) return null;
            const elegida = opcion.valor === valorActual;
            return (
              <li
                key={`${opcion.valor}-${indice}`}
                role="option"
                aria-selected={elegida}
                data-valor={opcion.valor}
                onMouseEnter={() => setActiva(indice)}
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => elegir(indice)}
                className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm ${
                  indice === activa ? "bg-papel-osc" : ""
                } ${elegida ? "font-bold text-fucsia-osc" : "font-medium"} ${opcion.valor === "" ? "text-tinta/50" : ""}`}
              >
                <span>{opcion.etiqueta}</span>
                {elegida && (
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12l5 5L20 7" />
                  </svg>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
