import Badge from "../ui/Badge";
import NationalBankLogo from "./NationalBankLogo";

const navItems = [
  { id: "overview", label: "Обзор" },
  { id: "queue", label: "Очередь" },
  { id: "sessions", label: "Сессии" },
  { id: "nodes", label: "Узлы" },
  { id: "users", label: "Пользователи" },
];

export default function AdminSidebar({ activeSection, onSectionChange, queueCount }) {
  return (
    <aside className="admin-sidebar">
      <div className="sidebar-brand">
        <NationalBankLogo className="sidebar-logo-mark" title="Национальный Банк" />
        <div>
          <h1>Национальный Банк</h1>
          <p>Контур администрирования</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            type="button"
            className={activeSection === item.id ? "active" : ""}
            onClick={() => onSectionChange(item.id)}
          >
            <span>{item.label}</span>
            {item.id === "queue" ? <Badge tone="yellow">{queueCount}</Badge> : null}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="live-dot" />
        <p>Статус кластера: онлайн</p>
      </div>
    </aside>
  );
}
