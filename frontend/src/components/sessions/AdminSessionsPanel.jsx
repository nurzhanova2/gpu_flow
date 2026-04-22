import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MeterBar from "../ui/MeterBar";
import StatusBadge from "../ui/StatusBadge";
import ActionButton from "../ui/ActionButton";

export default function AdminSessionsPanel({ sessions, onWarn, onTerminate, pendingActionId = null }) {
  return (
    <Card className="table-card">
      <div className="table-title-row">
        <h3>Контроль активных сессий</h3>
        <Badge tone="green">{sessions.length} в работе</Badge>
      </div>

      <div className="admin-session-list">
        {sessions.map((session) => (
          <article key={session.id} className="admin-session-row">
            <div className="admin-session-main">
              <div>
                <h4>{session.user}</h4>
                <p>{session.team} - {session.node} - {session.profile}</p>
              </div>
              <StatusBadge status={session.status} />
            </div>

            <div className="admin-session-usage">
              <div>
                <span>GPU</span>
                <MeterBar value={session.gpuUsage} compact tone={session.gpuUsage > 85 ? "red" : session.gpuUsage > 60 ? "yellow" : "green"} />
              </div>
              <div>
                <span>MEM</span>
                <MeterBar value={session.memUsage} compact tone={session.memUsage > 80 ? "red" : "blue"} />
              </div>
            </div>

            <div className="admin-session-footer">
              <span className="mono">{session.startedAt} - {session.durationMin}м</span>
              <div className="table-actions">
                <ActionButton
                  tone="default"
                  size="sm"
                  onClick={() => onWarn?.(session.id)}
                  disabled={pendingActionId === session.id}
                >
                  Предупредить
                </ActionButton>
                <ActionButton
                  tone="danger"
                  size="sm"
                  onClick={() => onTerminate?.(session.id)}
                  disabled={pendingActionId === session.id}
                >
                  Завершить
                </ActionButton>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
