const STATUS_TONES = {
  waiting: "muted",
  starting: "muted",
  running: "green",
  idle: "muted",
  failed: "muted",
  cancelled: "muted",
  terminating: "muted",
  terminated: "muted",
  completed: "green",
  standby: "muted",
  healthy: "green",
  degraded: "yellow",
  offline: "red",
  active: "green",
  queued: "muted",
  blocked: "red",
};

const STATUS_LABELS = {
  waiting: "Waiting",
  starting: "Starting",
  running: "Running",
  idle: "Idle",
  failed: "Failed",
  cancelled: "Cancelled",
  terminating: "Terminating",
  terminated: "Terminated",
  completed: "Completed",
  standby: "Standby",
  healthy: "Healthy",
  degraded: "Degraded",
  offline: "Offline",
  active: "Active",
  queued: "Queued",
  blocked: "Blocked",
};

export default function StatusBadge({ status }) {
  const normalized = (status || "").toLowerCase();
  const tone = STATUS_TONES[normalized] || "muted";
  const label = STATUS_LABELS[normalized] || status;

  return <span className={`status-badge status-badge-${tone}`}>{label}</span>;
}
