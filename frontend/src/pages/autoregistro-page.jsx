import { useEffect, useState } from "react";
import { enviarAutoregistro, obtenerAutoregistroPublico } from "../api/api-client";
import { Logotipo } from "../components/marca";
import { PoliticaDatos } from "../components/politica-datos";

const CLASE_CAMPO =
  "mt-1.5 w-full rounded-xl border-2 border-tinta/15 bg-white px-4 py-3 text-base outline-none transition focus:border-fucsia focus:ring-4 focus:ring-fucsia/15";

/**
 * Pagina publica de autorregistro de clientes (HU-07: RF-046 a RF-049). No pide inicio de sesion.
 *
 * El cliente lee el aviso y la politica vigentes, escribe sus datos y marca la aceptacion (obligatoria);
 * la casilla de promociones es aparte y viene desmarcada. La respuesta es la misma haya o no un registro
 * previo: no se revela si ya estaba. El campo "sitio_web" esta oculto para las personas y sirve de trampa
 * contra robots.
 *
 * @param {{token: string}} props Codigo del enlace, tomado de la direccion `/registro/<codigo>`.
 * @returns {JSX.Element}
 */
export function AutoregistroPage({ token }) {
  const [politica, setPolitica] = useState(null);
  const [noDisponible, setNoDisponible] = useState(null);
  const [valores, setValores] = useState({ nombre: "", documento: "", telefono: "", email: "", sitio_web: "" });
  const [acepta, setAcepta] = useState(false);
  const [aceptaPromociones, setAceptaPromociones] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);
  const [mensajeFinal, setMensajeFinal] = useState(null);

  useEffect(() => {
    let activo = true;
    obtenerAutoregistroPublico(token)
      .then((datos) => activo && setPolitica(datos))
      .catch((falla) => activo && setNoDisponible(falla.message || "Este enlace no está disponible."));
    return () => {
      activo = false;
    };
  }, [token]);

  /**
   * Cambia un campo del formulario; el telefono solo admite digitos.
   *
   * @param {string} campo
   * @param {string} valor
   */
  function cambiar(campo, valor) {
    setValores((actual) => ({ ...actual, [campo]: campo === "telefono" ? valor.replace(/\D/g, "") : valor }));
  }

  /**
   * Envia el registro.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    if (valores.telefono && valores.telefono.length < 7) {
      setError("El teléfono debe tener al menos 7 dígitos.");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const respuesta = await enviarAutoregistro(
        token,
        {
          nombre: valores.nombre.trim(),
          documento: valores.documento.trim() || null,
          telefono: valores.telefono || null,
          email: valores.email.trim() || null,
          acepta_politica: acepta,
          acepta_publicidad: aceptaPromociones,
          sitio_web: valores.sitio_web,
        }
      );
      setMensajeFinal(respuesta.mensaje);
    } catch (falla) {
      setError(falla.message || "No se pudo enviar el registro.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="min-h-screen bg-papel px-4 py-8">
      <div className="mx-auto w-full max-w-lg">
        <Logotipo grande />
        <h1 className="mt-6 font-display text-3xl font-extrabold">Regístrate como cliente</h1>

        {noDisponible && (
          <p role="alert" className="mt-6 rounded-2xl border border-fucsia/30 bg-fucsia/8 px-4 py-4 font-medium text-fucsia-osc">
            {noDisponible}
          </p>
        )}

        {!noDisponible && !politica && <p className="mt-6 text-tinta/60">Cargando…</p>}

        {mensajeFinal && (
          <p role="status" className="mt-6 rounded-2xl border border-turquesa/30 bg-turquesa/10 px-4 py-4 text-lg font-semibold text-turquesa">
            {mensajeFinal}
          </p>
        )}

        {politica && !mensajeFinal && (
          <form onSubmit={enviar} className="mt-4 space-y-4">
            <p className="text-tinta/70">Guardamos tus datos para llevar tus compras y darte descuentos.</p>
            <PoliticaDatos politica={politica} />

            <label className="block text-sm font-semibold">
              Nombre
              <input
                type="text"
                required
                maxLength={150}
                value={valores.nombre}
                onChange={(evento) => cambiar("nombre", evento.target.value)}
                autoComplete="name"
                className={CLASE_CAMPO}
              />
            </label>
            <label className="block text-sm font-semibold">
              Documento <span className="font-normal text-tinta/55">(opcional)</span>
              <input
                type="text"
                maxLength={30}
                value={valores.documento}
                onChange={(evento) => cambiar("documento", evento.target.value)}
                className={CLASE_CAMPO}
              />
            </label>
            <label className="block text-sm font-semibold">
              Teléfono <span className="font-normal text-tinta/55">(opcional)</span>
              <input
                type="tel"
                inputMode="numeric"
                maxLength={15}
                value={valores.telefono}
                onChange={(evento) => cambiar("telefono", evento.target.value)}
                autoComplete="tel"
                className={CLASE_CAMPO}
              />
            </label>
            <label className="block text-sm font-semibold">
              Correo <span className="font-normal text-tinta/55">(opcional)</span>
              <input
                type="email"
                maxLength={120}
                value={valores.email}
                onChange={(evento) => cambiar("email", evento.target.value)}
                autoComplete="email"
                className={CLASE_CAMPO}
              />
            </label>

            {/* Campo trampa: invisible y fuera del orden de tabulacion; solo un robot lo llena. */}
            <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
              <label>
                Sitio web
                <input
                  type="text"
                  tabIndex={-1}
                  autoComplete="off"
                  value={valores.sitio_web}
                  onChange={(evento) => cambiar("sitio_web", evento.target.value)}
                />
              </label>
            </div>

            <label className="flex items-start gap-3 rounded-xl border border-tinta/12 bg-white p-3 text-sm">
              <input
                type="checkbox"
                checked={acepta}
                onChange={(evento) => setAcepta(evento.target.checked)}
                className="mt-1 h-5 w-5 shrink-0"
              />
              <span>{politica.texto_autorizacion}</span>
            </label>
            <label className="flex items-start gap-3 rounded-xl border border-tinta/12 bg-white p-3 text-sm">
              <input
                type="checkbox"
                checked={aceptaPromociones}
                onChange={(evento) => setAceptaPromociones(evento.target.checked)}
                className="mt-1 h-5 w-5 shrink-0"
              />
              <span>{politica.texto_promociones}</span>
            </label>

            {error && (
              <p role="alert" className="text-sm font-medium text-fucsia-osc">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={enviando || !acepta}
              className="w-full rounded-2xl bg-fucsia px-4 py-3.5 font-display text-lg font-extrabold text-white disabled:opacity-50"
            >
              {enviando ? "Enviando…" : "Registrarme"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
