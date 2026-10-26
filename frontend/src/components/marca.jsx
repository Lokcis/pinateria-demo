/**
 * Logo oficial del negocio: PNG con fondo transparente (`public/logo-demo.png`, 1024 px de ancho).
 *
 * Es decorativo para los lectores de pantalla: el nombre del negocio siempre va escrito al lado.
 *
 * @param {{className?: string}} props
 * @returns {JSX.Element}
 */
export function LogoImagen({ className = "" }) {
  return (
    <img
      src="/logo-demo.png"
      alt=""
      aria-hidden="true"
      width={1024}
      height={719}
      draggable="false"
      className={className}
    />
  );
}

/**
 * Logotipo compacto: logo del negocio + nombre escrito.
 *
 * @param {{claro?: boolean, grande?: boolean}} props - `claro` invierte el color del texto (para fondos de color);
 *   `grande` agranda el logo (pantallas de inicio de sesion y de registro).
 * @returns {JSX.Element}
 */
export function Logotipo({ claro = false, grande = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <LogoImagen className={`${grande ? "h-16" : "h-10"} w-auto shrink-0`} />
      <div className="leading-none">
        <p className={`font-display text-lg font-extrabold ${claro ? "text-white" : "text-tinta"}`}>Piñatería Demo</p>
        <p
          className={`mt-0.5 text-[11px] font-semibold uppercase tracking-[0.18em] ${
            claro ? "text-white/75" : "text-tinta/55"
          }`}
        >
          Piñatería
        </p>
      </div>
    </div>
  );
}
