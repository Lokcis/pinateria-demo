import { BandejaNotificaciones } from "./bandeja-notificaciones";
import { ListaCompras } from "./lista-compras";

/**
 * Bandeja de notificaciones y lista de compras juntas (Adendo v2, mejora B1: HU-10).
 *
 * La usan el Dashboard del propietario (panel de notificaciones) y la pestaña "Stock bajo"
 * del administrador.
 *
 * @param {{alCambiarNoLeidas?: (noLeidas: number) => void}} props - Ver `BandejaNotificaciones`.
 * @returns {JSX.Element}
 */
export function StockBajo({ alCambiarNoLeidas }) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <BandejaNotificaciones alCambiarNoLeidas={alCambiarNoLeidas} />
      <ListaCompras />
    </div>
  );
}
