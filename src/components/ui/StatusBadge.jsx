const STATUS_TONES = {
  waiting: "muted",
  starting: "muted",
  running: "green",
  idle: "muted",
  failed: "muted",
  completed: "green",
  standby: "muted",
  healthy: "green",
  active: "green",
  queued: "muted",
};

const STATUS_LABELS = {
  waiting: "Waiting",
  starting: "Starting",
  running: "Running",
  idle: "Idle",
  failed: "Failed",
  completed: "Completed",
  standby: "Standby",
  healthy: "Healthy",
  active: "Active",
  queued: "Queued",
};

export default function StatusBadge({ status }) {
  const normalized = (status || "").toLowerCase();
  const tone = STATUS_TONES[normalized] || "muted";
  const label = STATUS_LABELS[normalized] || status;

  return <span className={`status-badge status-badge-${tone}`}>{label}</span>;
}
