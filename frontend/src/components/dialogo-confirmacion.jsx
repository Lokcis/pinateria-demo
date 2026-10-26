import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Cuadro de confirmacion propio de la app (reemplaza a `window.confirm`).
 *
 * @param {{
 *   titulo: string, mensaje?: string, aviso?: string, textoConfirmar: string, peligro?: boolean,
 *   alResponder: (confirmado: boolean) => void
 * }} props
 * @returns {JSX.Element}
 */
function DialogoConfirmacion({ titulo, mensaje, aviso, textoConfirmar, peligro, alResponder }) {
  const botonCancelar = useRef(null);

  useEffect(() => {
    botonCancelar.current?.focus();
    const alPulsar = (evento) => {
      if (evento.key === "Escape") alResponder(false);
    };
    document.addEventListener("keydown", alPulsar);
    return () => document.removeEventListener("keydown", alPulsar);
  }, [alResponder]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-tinta/50 p-4 backdrop-blur-[2px] sm:items-center"
      onClick={(evento) => evento.target === evento.currentTarget && alResponder(false)}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dialogo-titulo"
        className="w-full max-w-md animate-pop rounded-3xl bg-white p-6 shadow-2xl shadow-tinta/30"
      >
        <h2 id="dialogo-titulo" className="font-display text-xl font-extrabold">
          {titulo}
        </h2>
        {mensaje && <p className="mt-2 text-sm text-tinta/70">{mensaje}</p>}
        {aviso && (
          <p
            role="note"
            className="mt-3 rounded-xl border border-mandarina/30 bg-mandarina/10 px-3.5 py-2.5 text-sm font-medium text-tinta"
          >
            {aviso}
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-2.5">
          <button
            ref={botonCancelar}
            type="button"
            onClick={() => alResponder(false)}
            className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold transition hover:bg-papel"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => alResponder(true)}
            className={`rounded-xl px-4 py-2 text-sm font-bold text-white transition ${
              peligro ? "bg-fucsia hover:bg-fucsia-osc" : "bg-turquesa hover:opacity-90"
            }`}
          >
            {textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook para pedir confirmacion con un cuadro propio en vez de `window.confirm`.
 *
 * Uso: `const { confirmar, dialogo } = useConfirmar();` renderizar `{dialogo}`
 * en el componente y hacer `if (!(await confirmar({...}))) return;`.
 *
 * @returns {{
 *   confirmar: (opciones: {titulo: string, mensaje?: string, aviso?: string,
 *     textoConfirmar?: string, peligro?: boolean}) => Promise<boolean>,
 *   dialogo: JSX.Element | null
 * }}
 */
export function useConfirmar() {
  const [pedido, setPedido] = useState(null);

  const confirmar = useCallback(
    (opciones) => new Promise((resolver) => setPedido({ ...opciones, resolver })),
    []
  );

  const responder = useCallback(
    (confirmado) => {
      pedido?.resolver(confirmado);
      setPedido(null);
    },
    [pedido]
  );

  const dialogo = pedido ? (
    <DialogoConfirmacion
      titulo={pedido.titulo}
      mensaje={pedido.mensaje}
      aviso={pedido.aviso}
      textoConfirmar={pedido.textoConfirmar || "Confirmar"}
      peligro={pedido.peligro}
      alResponder={responder}
    />
  ) : null;

  return { confirmar, dialogo };
}
