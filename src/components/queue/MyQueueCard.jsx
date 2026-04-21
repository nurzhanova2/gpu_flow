import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MeterBar from "../ui/MeterBar";
import ActionButton from "../ui/ActionButton";
import StatusBadge from "../ui/StatusBadge";

export default function MyQueueCard({ sessionState, queueSnapshot }) {
  return (
    <Card>
      <div className="panel-head">
        <h3>Моя сессия</h3>
        <StatusBadge status={sessionState.status} />
      </div>

      <p className="muted-text">{sessionState.stateLabel}</p>

      <div className="mini-stat-grid">
        <div>
          <small>Позиция</small>
          <strong>{sessionState.queuePosition}</strong>
        </div>
        <div>
          <small>ETA</small>
          <strong>{sessionState.etaRange}</strong>
        </div>
        <div>
          <small>Запрос</small>
          <strong>{sessionState.requestedAt}</strong>
        </div>
      </div>

      <div className="queue-progress">
        <div>
          <p>Прогресс очереди</p>
          <span>{sessionState.completedAhead} из {sessionState.queuePosition + sessionState.completedAhead} завершено</span>
        </div>
        <MeterBar value={sessionState.progressPercent} tone="yellow" />
      </div>

      <div className="queue-extra-meta">
        <Badge tone="neutral">Профиль: {sessionState.selectedProfile}</Badge>
        <Badge tone="blue">Среднее сегодня: {sessionState.averageWaitToday}</Badge>
      </div>

      <div className="queue-action-row">
        <ActionButton tone="danger">Отменить очередь</ActionButton>
        <ActionButton tone="default">Повторить запрос</ActionButton>
      </div>

      <div className="queue-preview-list">
        {queueSnapshot.slice(0, 5).map((entry, index) => (
          <div className={`queue-preview-row ${entry.mine ? "queue-row-mine" : ""}`} key={entry.id}>
            <span className="mono">#{index + 1}</span>
            <span>{entry.user}</span>
            <Badge tone="neutral">{entry.profile}</Badge>
            <StatusBadge status={entry.status} />
            <span className="mono">{entry.waitMin}м</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
