import Badge from "../ui/Badge";

const levelToneMap = {
  critical: "red",
  warning: "yellow",
  info: "blue",
};

const levelTextMap = {
  critical: "Critical",
  warning: "Warning",
  info: "Info",
};

export default function AdminAlerts({ alerts }) {
  return (
    <section className="alert-list">
      {alerts.map((alert) => (
        <article key={alert.id} className={`alert-row alert-${alert.level}`}>
          <div>
            <p>{alert.message}</p>
            <small>{alert.createdAt}</small>
          </div>
          <Badge tone={levelToneMap[alert.level] || "neutral"}>{levelTextMap[alert.level] || alert.level}</Badge>
        </article>
      ))}
    </section>
  );
}
