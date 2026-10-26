import { useEffect, useRef, useState } from "react";
import { CambiarPassword } from "./cambiar-password";
import { Logotipo } from "./marca";

const ETIQUETA_ROL = {
  vendedor: "Vendedor",
  administrador: "Administrador",
  propietario: "Propietario",
};

/**
 * Encabezado compacto: marca y menu de la cuenta (rol, cambiar contrasena y cerrar sesion).
 *
 * Los dos botones de cuenta van dentro de un menu para no ocupar la barra, que en celular es muy angosta.
 *
 * @param {{usuario: {sub?: string, rol?: string} | null, alCerrarSesion: () => void}} props
 * @returns {JSX.Element}
 */
export function Encabezado({ usuario, alCerrarSesion }) {
  const [abierto, setAbierto] = useState(false);
  const raiz = useRef(null);
  const rol = ETIQUETA_ROL[usuario?.rol] || usuario?.rol || "";

  useEffect(() => {
    if (!abierto) return undefined;
    const alPulsarFuera = (evento) => {
      if (raiz.current && !raiz.current.contains(evento.target)) setAbierto(false);
    };
    const alTeclear = (evento) => {
      if (evento.key === "Escape") setAbierto(false);
    };
    document.addEventListener("mousedown", alPulsarFuera);
    document.addEventListener("keydown", alTeclear);
    return () => {
      document.removeEventListener("mousedown", alPulsarFuera);
      document.removeEventListener("keydown", alTeclear);
    };
  }, [abierto]);

  return (
    <header className="sticky top-0 z-30 border-b border-tinta/10 bg-white">
      <div className="banderines banderines-finos" aria-hidden="true" />
      <div className="mx-auto flex max-w-[90rem] items-center justify-between gap-3 px-4 py-2 sm:px-6">
        <Logotipo />
        <div ref={raiz} className="relative">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={abierto}
            aria-label={`Cuenta: ${rol}`}
            onClick={() => setAbierto((valor) => !valor)}
            className="flex items-center gap-2 rounded-xl border border-tinta/15 py-1.5 pl-1.5 pr-3 text-sm font-semibold transition hover:border-tinta hover:bg-papel"
          >
            <span className="grid h-7 w-7 place-items-center rounded-full bg-fucsia text-xs font-extrabold text-white" aria-hidden="true">
              {rol.charAt(0)}
            </span>
            <span className="hidden sm:inline">{rol}</span>
            <span aria-hidden="true" className="text-tinta/50">
              ▾
            </span>
          </button>

          {abierto && (
            <div
              role="menu"
              aria-label="Cuenta"
              className="absolute right-0 top-full z-50 mt-2 w-56 animate-pop rounded-2xl border border-tinta/10 bg-white p-2 shadow-xl shadow-tinta/15"
            >
              <p className="px-3 pb-1 pt-1.5 text-xs font-semibold uppercase tracking-wider text-tinta/50">Sesión: {rol}</p>
              <CambiarPassword className="block w-full rounded-lg px-3 py-2 text-left text-sm font-semibold hover:bg-papel" />
              <button
                type="button"
                role="menuitem"
                onClick={alCerrarSesion}
                className="block w-full rounded-lg px-3 py-2 text-left text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10"
              >
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
