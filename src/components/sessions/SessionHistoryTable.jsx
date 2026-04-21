import Card from "../ui/Card";
import Badge from "../ui/Badge";
import ActionButton from "../ui/ActionButton";

function toneFromResult(result) {
  if (result === "completed") return "green";
  return "neutral";
}

function resultLabel(result) {
  if (result === "completed") return "Completed";
  if (result === "failed") return "Failed";
  return result;
}

export default function SessionHistoryTable({ items }) {
  return (
    <Card className="table-card">
      <div className="table-title-row">
        <h3>История сессий</h3>
        <Badge tone="neutral">{items.length} записей</Badge>
      </div>

      <div className="table-head table-grid-history">
        <span>Начало</span>
        <span>Длительность</span>
        <span>Профиль</span>
        <span>Status</span>
        <span className="table-align-right">Action</span>
      </div>

      {items.map((item) => (
        <div key={item.id} className="table-row table-grid-history">
          <span>{item.startedAt}</span>
          <span>{item.duration}</span>
          <span><Badge tone="neutral">{item.profile}</Badge></span>
          <span><Badge tone={toneFromResult(item.result)}>{resultLabel(item.result)}</Badge></span>
          <div className="table-actions">
            <ActionButton tone="default" size="sm">Повторить</ActionButton>
          </div>
        </div>
      ))}
    </Card>
  );
}
