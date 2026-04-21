export default function MeterBar({ value, tone = "green", compact = false }) {
  return (
    <div className={`meter ${compact ? "meter-compact" : ""}`}>
      <div className={`meter-fill meter-fill-${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
