import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MeterBar from "../ui/MeterBar";
import ActionButton from "../ui/ActionButton";
import StatusBadge from "../ui/StatusBadge";

const EMPTY_STATE = {
  status: "waiting",
  stateLabel: "Активных заявок в очереди нет",
  queuePosition: 0,
  etaRange: "-",
  requestedAt: "-",
  completedAhead: 0,
  progressPercent: 0,
  selectedProfile: "-",
  averageWaitToday: "-",
};

export default function MyQueueCard({
  sessionState,
  queueSnapshot,
  onCancelQueue,
  onRelaunch,
  cancelPending = false,
  relaunchPending = false,
}) {
  const state = sessionState || EMPTY_STATE;
  const totalProgress = state.queuePosition + state.completedAhead;

  return (
    <Card>
      <div className="panel-head">
        <h3>Моя сессия</h3>
        <StatusBadge status={state.status} />
      </div>

      <p className="muted-text">{state.stateLabel}</p>

      <div className="mini-stat-grid">
        <div>
          <small>Позиция</small>
          <strong>{state.queuePosition}</strong>
        </div>
        <div>
          <small>ETA</small>
          <strong>{state.etaRange}</strong>
        </div>
        <div>
          <small>Запрос</small>
          <strong>{state.requestedAt}</strong>
        </div>
      </div>

      <div className="queue-progress">
        <div>
          <p>Прогресс очереди</p>
          <span>{state.completedAhead} из {totalProgress > 0 ? totalProgress : 0} завершено</span>
        </div>
        <MeterBar value={state.progressPercent} tone="yellow" />
      </div>

      <div className="queue-extra-meta">
        <Badge tone="neutral">Профиль: {state.selectedProfile}</Badge>
        <Badge tone="blue">Среднее сегодня: {state.averageWaitToday}</Badge>
      </div>

      <div className="queue-action-row">
        <ActionButton tone="danger" onClick={onCancelQueue} disabled={!sessionState || cancelPending}>
          {cancelPending ? "Отмена..." : "Отменить очередь"}
        </ActionButton>
        <ActionButton tone="default" onClick={onRelaunch} disabled={relaunchPending}>
          {relaunchPending ? "Повтор..." : "Повторить запрос"}
        </ActionButton>
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
