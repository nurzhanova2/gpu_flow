import Badge from "../ui/Badge";
import Card from "../ui/Card";
import ActionButton from "../ui/ActionButton";

function toneFromStatus(status) {
  if (status === "active") return "green";
  return "neutral";
}

export default function UserActivityTable({ rows }) {
  return (
    <Card className="table-card">
      <div className="table-title-row">
        <h3>Активность пользователей</h3>
        <Badge tone="blue">Последние 7 дней</Badge>
      </div>

      <div className="table-head table-grid-user-activity">
        <span>User</span>
        <span>Team</span>
        <span>Launches</span>
        <span>Active</span>
        <span>Queued</span>
        <span>Avg Runtime</span>
        <span>Status</span>
        <span className="table-align-right">Actions</span>
      </div>

      {rows.map((row) => (
        <div key={row.id} className="table-row table-grid-user-activity">
          <span>{row.user}</span>
          <span>{row.team}</span>
          <span>{row.launches7d}</span>
          <span>{row.active}</span>
          <span>{row.queued}</span>
          <span>{row.avgRuntime}</span>
          <span><Badge tone={toneFromStatus(row.status)}>{row.status}</Badge></span>
          <div className="table-actions">
            <ActionButton tone="default" size="sm">Лимиты</ActionButton>
            <ActionButton tone="danger" size="sm">Блок</ActionButton>
          </div>
        </div>
      ))}
    </Card>
  );
}
