import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { loginRequest, meRequest, registerRequest } from "../api/authApi";
import { setApiAuthHandlers } from "../api/client";

const TOKEN_KEY = "gpuflow.access_token";
const USER_KEY = "gpuflow.user";

const AuthContext = createContext(null);

function readStoredUser() {
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function readStoredToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function persistAuth(token, user) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => readStoredToken());
  const [user, setUser] = useState(() => readStoredUser());
  const [authReady, setAuthReady] = useState(false);
  const [forcedReason, setForcedReason] = useState("");

  const logout = useCallback((reason = "") => {
    clearAuth();
    setAccessToken(null);
    setUser(null);
    setForcedReason(reason);
  }, []);

  useEffect(() => {
    setApiAuthHandlers({
      onUnauthorized: () => logout("Сессия истекла. Выполните вход снова."),
      onBlocked: () => logout("Пользователь заблокирован администратором."),
    });
  }, [logout]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!accessToken) {
        setAuthReady(true);
        return;
      }

      try {
        const me = await meRequest(accessToken);
        if (!cancelled) {
          setUser(me);
        }
      } catch {
        if (!cancelled) {
          logout("Сессия недействительна. Выполните вход снова.");
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [accessToken, logout]);

  const login = useCallback(async (payload) => {
    const response = await loginRequest(payload);
    persistAuth(response.access_token, response.user);
    setAccessToken(response.access_token);
    setUser(response.user);
    setForcedReason("");
    return response.user;
  }, []);

  const register = useCallback(async (payload) => {
    const response = await registerRequest(payload);
    persistAuth(response.access_token, response.user);
    setAccessToken(response.access_token);
    setUser(response.user);
    setForcedReason("");
    return response.user;
  }, []);

  const clearForcedReason = useCallback(() => setForcedReason(""), []);

  const value = useMemo(
    () => ({
      accessToken,
      user,
      isAuthenticated: Boolean(accessToken && user),
      authReady,
      forcedReason,
      clearForcedReason,
      login,
      register,
      logout,
    }),
    [accessToken, user, authReady, forcedReason, clearForcedReason, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
