import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { iniciarSesion as iniciarSesionApi } from "../api/api-client";

const CLAVE_TOKEN_STORAGE = "mm_pos_token";

const AuthContext = createContext(null);

/**
 * Decodifica el payload de un JWT SIN verificar su firma.
 *
 * Uso exclusivamente para mostrar informacion en la interfaz (ej. el rol
 * del usuario actual); la validacion real de firma/expiracion la hace
 * siempre el backend en cada request. Nunca usar el resultado de esta
 * funcion para tomar decisiones de seguridad en el frontend.
 *
 * @param {string} token - Access token JWT.
 * @returns {{sub?: string, rol?: string} | null} El payload decodificado,
 *   o null si el token esta mal formado.
 */
function decodificarPayloadToken(token) {
  try {
    const partes = token.split(".");
    if (partes.length !== 3) {
      return null;
    }
    const payloadBase64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payloadBase64));
  } catch {
    return null;
  }
}

/**
 * Provee el estado de autenticacion (token JWT y usuario actual) a toda la app.
 *
 * @param {{children: React.ReactNode}} props
 * @returns {JSX.Element}
 */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(CLAVE_TOKEN_STORAGE));
  const [usuarioActual, setUsuarioActual] = useState(() => {
    const tokenGuardado = localStorage.getItem(CLAVE_TOKEN_STORAGE);
    return tokenGuardado ? decodificarPayloadToken(tokenGuardado) : null;
  });
  const [errorLogin, setErrorLogin] = useState(null);

  const iniciarSesion = useCallback(async (username, password) => {
    setErrorLogin(null);
    try {
      const resultado = await iniciarSesionApi(username, password);
      localStorage.setItem(CLAVE_TOKEN_STORAGE, resultado.access_token);
      setToken(resultado.access_token);
      setUsuarioActual(decodificarPayloadToken(resultado.access_token));
      return true;
    } catch (error) {
      setErrorLogin(error.message || "No se pudo iniciar sesion.");
      return false;
    }
  }, []);

  const cerrarSesion = useCallback(() => {
    localStorage.removeItem(CLAVE_TOKEN_STORAGE);
    setToken(null);
    setUsuarioActual(null);
  }, []);

  const valor = useMemo(
    () => ({ token, usuarioActual, errorLogin, iniciarSesion, cerrarSesion }),
    [token, usuarioActual, errorLogin, iniciarSesion, cerrarSesion]
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

/**
 * Hook de acceso al contexto de autenticacion.
 *
 * @returns {{
 *   token: string | null,
 *   usuarioActual: {sub?: string, rol?: string} | null,
 *   errorLogin: string | null,
 *   iniciarSesion: (username: string, password: string) => Promise<boolean>,
 *   cerrarSesion: () => void,
 * }}
 * @throws {Error} Si se usa fuera de un `AuthProvider`.
 */
export function useAuth() {
  const contexto = useContext(AuthContext);
  if (contexto === null) {
    throw new Error("useAuth debe usarse dentro de un AuthProvider.");
  }
  return contexto;
}
