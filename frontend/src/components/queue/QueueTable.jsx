import Card from "../ui/Card";
import Badge from "../ui/Badge";
import StatusBadge from "../ui/StatusBadge";
import ActionButton from "../ui/ActionButton";

export default function QueueTable({ rows, onPromote, onDelete, pendingActionId = null }) {
  return (
    <Card className="table-card">
      <div className="table-title-row">
        <h3>Управление очередью</h3>
        <Badge tone="yellow">{rows.length} запросов</Badge>
      </div>

      <div className="table-head table-grid-queue">
        <span>#</span>
        <span>User</span>
        <span>Team</span>
        <span>Status</span>
        <span>Профиль</span>
        <span>Узел</span>
        <span>Ожидание</span>
        <span>Причина</span>
        <span className="table-align-right">Actions</span>
      </div>

      {rows.map((row, index) => (
        <div key={row.id} className="table-row table-grid-queue">
          <span className="mono">{index + 1}</span>
          <span>{row.user}</span>
          <span>{row.team}</span>
          <span><StatusBadge status={row.status} /></span>
          <span><Badge tone="neutral">{row.profile}</Badge></span>
          <span>{row.nodeTarget}</span>
          <span className="mono">{row.waitMin}м</span>
          <span className="truncate">{row.reason}</span>
          <div className="table-actions">
            <ActionButton
              tone="default"
              size="sm"
              onClick={() => onPromote?.(row.id)}
              disabled={pendingActionId === row.id}
            >
              Поднять
            </ActionButton>
            <ActionButton
              tone="danger"
              size="sm"
              onClick={() => onDelete?.(row.id)}
              disabled={pendingActionId === row.id}
            >
              Удалить
            </ActionButton>
          </div>
        </div>
      ))}
    </Card>
  );
}
