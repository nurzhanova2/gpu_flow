import { useState } from "react";
import ViewSwitcher from "./components/layout/ViewSwitcher";
import UserDashboard from "./pages/UserDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import NationalBankLogo from "./components/layout/NationalBankLogo";

export default function App() {
  const [view, setView] = useState("user");

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
        <ViewSwitcher view={view} onChange={setView} />
      </div>

      <div className="app-content">
        {view === "user" ? <UserDashboard /> : <AdminDashboard />}
      </div>
    </div>
  );
}
