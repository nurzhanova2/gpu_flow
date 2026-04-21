import Card from "./Card";

export default function StatCard({ label, value, hint, tone = "neutral" }) {
  return (
    <Card className="stat-card" muted>
      <p className="stat-label">{label}</p>
      <p className={`stat-value stat-value-${tone}`}>{value}</p>
      {hint ? <p className="stat-hint">{hint}</p> : null}
    </Card>
  );
}
