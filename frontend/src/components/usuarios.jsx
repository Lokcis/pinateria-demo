import { useCallback, useEffect, useState } from "react";
import { crearUsuario, editarUsuario, obtenerUsuarios, restablecerPassword } from "../api/api-client";
import { Desplegable } from "./desplegable";
import { useAuth } from "../context/auth-context";
import { useConfirmar } from "./dialogo-confirmacion";

const ROLES = [
  { id: "administrador", etiqueta: "Administrador" },
  { id: "vendedor", etiqueta: "Vendedor" },
  { id: "propietario", etiqueta: "Propietario" },
];
const ETIQUETA_ROL = Object.fromEntries(ROLES.map(({ id, etiqueta }) => [id, etiqueta]));
const CLASE_INPUT = "w-full rounded-lg border border-tinta/20 bg-white px-3 py-2";

/**
 * Formulario de alta/edicion de un usuario (RF-015). En el alta pide la contrasena temporal.
 *
 * @param {{usuario?: object, esYo: boolean, alGuardar: () => void, alCancelar: () => void}} props
 *   `usuario` presente indica edicion; `esYo` bloquea el cambio de rol propio.
 * @returns {JSX.Element}
 */
function FormularioUsuario({ usuario, esYo, alGuardar, alCancelar }) {
  const { token } = useAuth();
  const [valores, setValores] = useState({
    nombre: usuario?.nombre ?? "",
    username: usuario?.username ?? "",
    rol: usuario?.rol ?? "vendedor",
    password: "",
  });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Envia el formulario al backend.
   *
   * @param {React.FormEvent} evento
   * @returns {Promise<void>}
   */
  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      if (usuario) {
        await editarUsuario(
          usuario.id,
          { nombre: valores.nombre.trim(), username: valores.username.trim(), rol: valores.rol },
          token
        );
      } else {
        await crearUsuario({ ...valores, nombre: valores.nombre.trim(), username: valores.username.trim() }, token);
      }
      alGuardar();
    } catch (falla) {
      setError(falla.message || "No se pudo guardar el usuario.");
    } finally {
      setEnviando(false);
    }
  }

  const cambiar = (campo) => (evento) => setValores((actual) => ({ ...actual, [campo]: evento.target.value }));

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-2xl border border-tinta/10 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-extrabold">{usuario ? "Editar usuario" : "Nuevo usuario"}</h3>
      <div className="grid gap-2.5 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Nombre</span>
          <input value={valores.nombre} onChange={cambiar("nombre")} required maxLength={120} className={CLASE_INPUT} />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Usuario</span>
          <input
            value={valores.username}
            onChange={cambiar("username")}
            required
            minLength={3}
            maxLength={60}
            pattern="[A-Za-z0-9._\-]+"
            title="Letras, números, punto, guion o guion bajo"
            autoComplete="off"
            className={CLASE_INPUT}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium text-tinta/70">Rol</span>
          <Desplegable value={valores.rol} onChange={cambiar("rol")} disabled={esYo} className={CLASE_INPUT}>
            {ROLES.map(({ id, etiqueta }) => (
              <option key={id} value={id}>
                {etiqueta}
              </option>
            ))}
          </Desplegable>
        </label>
        {!usuario && (
          <label className="text-sm">
            <span className="mb-1 block font-medium text-tinta/70">Contraseña temporal</span>
            <input
              type="password"
              value={valores.password}
              onChange={cambiar("password")}
              required
              minLength={8}
              maxLength={72}
              autoComplete="new-password"
              className={CLASE_INPUT}
            />
          </label>
        )}
      </div>
      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {enviando ? "Guardando…" : "Guardar"}
        </button>
        <button type="button" onClick={alCancelar} className="rounded-xl border border-tinta/20 px-4 py-2 text-sm font-semibold hover:bg-papel">
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * Gestion de usuarios y roles (RF-015). Solo administrador; el backend responde 403 al resto.
 *
 * @returns {JSX.Element}
 */
export function Usuarios() {
  const { token, usuarioActual } = useAuth();
  const { confirmar, dialogo } = useConfirmar();
  const [usuarios, setUsuarios] = useState(null);
  const [formulario, setFormulario] = useState(null); // null | "nuevo" | objeto usuario
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setUsuarios(await obtenerUsuarios(token));
    } catch (falla) {
      setError(falla.message || "No se pudo cargar la lista de usuarios.");
      setUsuarios([]);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const esYo = (usuario) => String(usuario.id) === String(usuarioActual?.sub);

  /**
   * Activa o desactiva una cuenta tras confirmar (nunca se borra).
   *
   * @param {object} usuario
   * @returns {Promise<void>}
   */
  async function alternarActivo(usuario) {
    const accion = usuario.activo ? "desactivar" : "reactivar";
    const acepta = await confirmar({
      titulo: `¿Quieres ${accion} a ${usuario.nombre}?`,
      mensaje: usuario.activo
        ? "No podrá iniciar sesión, pero su historial se conserva."
        : "Podrá volver a iniciar sesión.",
      textoConfirmar: usuario.activo ? "Desactivar" : "Reactivar",
      peligro: usuario.activo,
    });
    if (!acepta) return;
    setAviso(null);
    try {
      await editarUsuario(usuario.id, { activo: !usuario.activo }, token);
      await cargar();
    } catch (falla) {
      setError(falla.message || "No se pudo actualizar el usuario.");
    }
  }

  /**
   * Pide una contrasena temporal y la fija para el usuario.
   *
   * @param {object} usuario
   * @returns {Promise<void>}
   */
  async function restablecer(usuario) {
    const temporal = window.prompt(`Nueva contraseña temporal para ${usuario.nombre} (mínimo 8 caracteres):`);
    if (temporal === null) return;
    setError(null);
    setAviso(null);
    try {
      await restablecerPassword(usuario.id, temporal, token);
      setAviso(`Contraseña de ${usuario.nombre} restablecida.`);
    } catch (falla) {
      setError(falla.message || "No se pudo restablecer la contraseña.");
    }
  }

  return (
    <section className="space-y-4">
      {dialogo}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-xl font-extrabold">Usuarios</h2>
        <button type="button" onClick={() => setFormulario("nuevo")} className="rounded-xl bg-fucsia px-4 py-2 text-sm font-bold text-white">
          Nuevo usuario
        </button>
      </div>

      {formulario && (
        <FormularioUsuario
          key={formulario === "nuevo" ? "nuevo" : formulario.id}
          usuario={formulario === "nuevo" ? undefined : formulario}
          esYo={formulario !== "nuevo" && esYo(formulario)}
          alGuardar={() => {
            setFormulario(null);
            cargar();
          }}
          alCancelar={() => setFormulario(null)}
        />
      )}

      {error && (
        <p role="alert" className="text-sm font-medium text-fucsia-osc">
          {error}
        </p>
      )}
      {aviso && (
        <p role="status" className="text-sm font-medium text-tinta/80">
          {aviso}
        </p>
      )}
      {usuarios === null && <p className="text-tinta/60">Cargando…</p>}

      <ul className="space-y-2">
        {usuarios?.map((usuario) => (
          <li
            key={usuario.id}
            className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-tinta/10 bg-white p-4 ${
              usuario.activo ? "" : "opacity-60"
            }`}
          >
            <div className="min-w-0 text-sm">
              <p className="font-bold">
                {usuario.nombre}
                {esYo(usuario) && <span className="ml-2 text-xs font-semibold text-tinta/50">(tú)</span>}
              </p>
              <p className="text-tinta/70">
                {usuario.username} · {ETIQUETA_ROL[usuario.rol] || usuario.rol} · {usuario.activo ? "Activo" : "Inactivo"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setFormulario(usuario)} aria-label={`Editar ${usuario.nombre}`} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel">
                Editar
              </button>
              <button type="button" onClick={() => restablecer(usuario)} aria-label={`Restablecer contraseña de ${usuario.nombre}`} className="rounded-lg border border-tinta/20 px-3 py-1.5 text-sm font-semibold hover:bg-papel">
                Restablecer contraseña
              </button>
              {!esYo(usuario) && (
                <button
                  type="button"
                  onClick={() => alternarActivo(usuario)}
                  aria-label={`${usuario.activo ? "Desactivar" : "Reactivar"} ${usuario.nombre}`}
                  className="rounded-lg border border-fucsia/40 px-3 py-1.5 text-sm font-semibold text-fucsia-osc hover:bg-fucsia/10"
                >
                  {usuario.activo ? "Desactivar" : "Reactivar"}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
