export default function ViewSwitcher({ view, onChange }) {
  return (
    <div className="view-switcher">
      <button
        type="button"
        className={view === "user" ? "active" : ""}
        onClick={() => onChange("user")}
      >
        Панель пользователя
      </button>
      <button
        type="button"
        className={view === "admin" ? "active" : ""}
        onClick={() => onChange("admin")}
      >
        Панель администратора
      </button>
    </div>
  );
}
