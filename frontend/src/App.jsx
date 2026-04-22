import { useCallback, useEffect, useMemo, useState } from "react";
import ViewSwitcher from "./components/layout/ViewSwitcher";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import NationalBankLogo from "./components/layout/NationalBankLogo";
import ActionButton from "./components/ui/ActionButton";
import Badge from "./components/ui/Badge";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";

function normalizePath(pathname) {
  if (!pathname || pathname === "/") return "/login";
  const clean = pathname.replace(/\/+$/, "") || "/";
  if (["/login", "/register", "/user", "/admin"].includes(clean)) return clean;
  return "/login";
}

export default function App() {
  const { user, isAuthenticated, authReady, logout } = useAuth();
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));

  const navigate = useCallback((nextPath, replace = false) => {
    const normalized = normalizePath(nextPath);
    if (replace) {
      window.history.replaceState({}, "", normalized);
    } else {
      window.history.pushState({}, "", normalized);
    }
    setPath(normalized);
  }, []);

  useEffect(() => {
    const onPopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!authReady) return;

    if (!isAuthenticated) {
      if (path !== "/login" && path !== "/register") {
        navigate("/login", true);
      }
      return;
    }

    if (path === "/login" || path === "/register") {
      navigate(user?.role === "admin" ? "/admin" : "/user", true);
      return;
    }

    if (path === "/admin" && user?.role !== "admin") {
      navigate("/user", true);
    }
  }, [authReady, isAuthenticated, navigate, path, user]);

  const isAuthPage = path === "/login" || path === "/register";

  const currentView = useMemo(() => {
    if (path === "/admin") return "admin";
    return "user";
  }, [path]);

  if (!authReady) {
    return (
      <div className="app-root">
        <div className="auth-screen">
          <div className="auth-loading">Проверка сессии...</div>
        </div>
      </div>
    );
  }

  if (isAuthPage) {
    return (
      <div className="app-root">
        <div className="app-topbar auth-topbar">
          <div className="topbar-brand">
            <NationalBankLogo className="topbar-logo" title="Национальный Банк" />
            <div>
              <p className="topbar-eyebrow">GPU Очередь и JupyterHub</p>
              <h1 className="topbar-title">Центр управления Национального Банка</h1>
            </div>
          </div>
          <Badge tone="neutral">Авторизация</Badge>
        </div>

        <div className="app-content">
          {path === "/login" ? (
            <LoginPage onOpenRegister={() => navigate("/register")} />
          ) : (
            <RegisterPage onOpenLogin={() => navigate("/login")} />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app-root">
      <div className="app-topbar">
        <div className="topbar-brand">
          <NationalBankLogo className="topbar-logo" title="Национальный Банк" />
          <div>
            <p className="topbar-eyebrow">GPU Очередь и JupyterHub</p>
            <h1 className="topbar-title">Центр управления Национального Банка</h1>
          </div>
        </div>

        <div className="topbar-controls">
          {user?.role === "admin" ? (
            <ViewSwitcher view={currentView} onChange={(view) => navigate(view === "admin" ? "/admin" : "/user")} />
          ) : (
            <Badge tone="green">Панель пользователя</Badge>
          )}
          <ActionButton tone="default" onClick={() => logout("Вы вышли из системы.")}>Выйти</ActionButton>
        </div>
      </div>

      <div className="app-content">
        {path === "/admin" ? <AdminDashboard /> : <UserDashboard />}
      </div>
    </div>
  );
}
