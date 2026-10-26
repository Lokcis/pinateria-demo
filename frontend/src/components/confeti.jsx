import { useMemo } from "react";

const COLORES = ["#d6245f", "#ffb800", "#0b7f72", "#f26a2e", "#2b74e0"];
const CANTIDAD_PAPELITOS = 26;

/**
 * Ráfaga breve de papelitos, disparada al confirmar una venta.
 *
 * Cambiar `disparo` (ej. el id de la venta) genera una nueva ráfaga.
 * Es puramente decorativa (`aria-hidden`) y `prefers-reduced-motion` la
 * reduce a un instante (ver `app.css`).
 *
 * @param {{disparo: number | string}} props
 * @returns {JSX.Element}
 */
export function Confeti({ disparo }) {
  const papelitos = useMemo(
    () =>
      Array.from({ length: CANTIDAD_PAPELITOS }, (_, indice) => {
        const angulo = (Math.PI * 2 * indice) / CANTIDAD_PAPELITOS + Math.random() * 0.4;
        const distancia = 90 + Math.random() * 130;
        return {
          id: indice,
          color: COLORES[indice % COLORES.length],
          dx: Math.cos(angulo) * distancia,
          dy: Math.sin(angulo) * distancia - 40,
          giro: (Math.random() - 0.5) * 720,
          ancho: 6 + Math.random() * 6,
          alto: 10 + Math.random() * 8,
          redondo: indice % 3 === 0,
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [disparo]
  );

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-visible">
      <div className="absolute left-1/2 top-1/2">
        {papelitos.map((p) => (
          <span
            key={`${disparo}-${p.id}`}
            className="absolute animate-confeti"
            style={{
              "--dx": `${p.dx}px`,
              "--dy": `${p.dy}px`,
              "--giro": `${p.giro}deg`,
              width: p.ancho,
              height: p.redondo ? p.ancho : p.alto,
              borderRadius: p.redondo ? "9999px" : "2px",
              backgroundColor: p.color,
            }}
          />
        ))}
      </div>
    </div>
  );
}
