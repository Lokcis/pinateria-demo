import { useState } from "react";
import { useAuth } from "../context/auth-context";
import { LogoImagen, Logotipo } from "./marca";

const CLASE_CAMPO =
  "mt-1.5 w-full rounded-xl border-2 border-tinta/15 bg-white px-4 py-3 text-lg outline-none transition focus:border-fucsia focus:ring-4 focus:ring-fucsia/15";

/**
 * Pantalla de inicio de sesion.
 *
 * @returns {JSX.Element}
 */
export function LoginForm() {
  const { iniciarSesion, errorLogin } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [enviando, setEnviando] = useState(false);

  /**
   * Maneja el submit del formulario de login.
   *
   * @param {React.FormEvent<HTMLFormElement>} evento
   * @returns {Promise<void>}
   */
  async function manejarSubmit(evento) {
    evento.preventDefault();
    setEnviando(true);
    await iniciarSesion(username, password);
    setEnviando(false);
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-fucsia p-10 text-white lg:flex">
        <Logotipo claro />
        <div className="relative z-10 max-w-md">
          <h2 className="font-display text-5xl font-extrabold leading-[1.05]">Cada fiesta empieza con una buena venta.</h2>
          <p className="mt-4 text-lg text-white/85">Punto de venta e inventario de Piñatería Demo.</p>
        </div>
        <div className="sombra-dura absolute right-10 top-24 w-80 rotate-3 rounded-[2rem] border-2 border-tinta bg-papel p-6">
          <LogoImagen className="h-auto w-full" />
        </div>
        <div className="banderines absolute inset-x-0 bottom-0 opacity-95" aria-hidden="true" />
      </div>

      <div className="flex flex-col justify-center px-6 py-10 sm:px-12">
        <div className="mb-8 lg:hidden">
          <Logotipo grande />
        </div>
        <form className="login-form mx-auto w-full max-w-sm" onSubmit={manejarSubmit}>
          <h1 className="font-display text-3xl font-extrabold">Bienvenido</h1>
          <p className="mt-1 text-tinta/65">Ingresa con tu usuario para abrir la caja.</p>

          <label htmlFor="username" className="mt-7 block text-sm font-semibold">
            Usuario
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(evento) => setUsername(evento.target.value)}
            autoComplete="username"
            required
            className={CLASE_CAMPO}
          />

          <label htmlFor="password" className="mt-4 block text-sm font-semibold">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(evento) => setPassword(evento.target.value)}
            autoComplete="current-password"
            required
            className={CLASE_CAMPO}
          />

          {errorLogin && (
            <p
              role="alert"
              className="mensaje-error mt-4 rounded-xl border border-fucsia/30 bg-fucsia/8 px-3 py-2.5 text-sm font-medium text-fucsia-osc"
            >
              {errorLogin}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="sombra-dura mt-6 w-full rounded-2xl border-2 border-tinta bg-fucsia px-4 py-3.5 font-display text-lg font-extrabold text-white transition enabled:hover:bg-fucsia-osc enabled:active:translate-x-1 enabled:active:translate-y-1 enabled:active:shadow-none disabled:opacity-60"
          >
            {enviando ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
      </div>
    </div>
  );
}
