import { AuthProvider, useAuth } from "./context/auth-context";
import { AvisoValidacion } from "./components/aviso-validacion";
import { LoginForm } from "./components/login-form";
import { DashboardPage } from "./pages/dashboard-page";
import { PosPage } from "./pages/pos-page";
import { AutoregistroPage } from "./pages/autoregistro-page";
import "./app.css";

/**
 * Selecciona que pantalla mostrar segun el estado de autenticacion.
 *
 * @returns {JSX.Element}
 */
function ContenidoPrincipal() {
  const { token, usuarioActual } = useAuth();
  if (!token) {
    return <LoginForm />;
  }
  return usuarioActual?.rol === "propietario" ? <DashboardPage /> : <PosPage />;
}

/**
 * Componente raiz de la aplicacion. `AvisoValidacion` reemplaza los globos de validacion del navegador en toda la app. La pagina publica de autorregistro (`/registro/<codigo>`) no pasa por el login.
 *
 * @returns {JSX.Element}
 */
export function App() {
  // Ruta publica del autorregistro (sin sesion): /registro/<codigo>. El resto de la app exige iniciar sesion.
  const coincidencia = window.location.pathname.match(/^\/registro\/([^/]+)\/?$/);
  if (coincidencia) {
    return (
      <>
        <AutoregistroPage token={decodeURIComponent(coincidencia[1])} />
        <AvisoValidacion />
      </>
    );
  }
  return (
    <AuthProvider>
      <ContenidoPrincipal />
      <AvisoValidacion />
    </AuthProvider>
  );
}
