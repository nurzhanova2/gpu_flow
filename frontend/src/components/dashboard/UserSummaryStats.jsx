import StatCard from "../ui/StatCard";

export default function UserSummaryStats({ stats }) {
  return (
    <section className="stats-grid">
      {stats.map((stat) => (
        <StatCard key={stat.id} label={stat.label} value={stat.value} hint={stat.hint} tone={stat.tone} />
      ))}
    </section>
  );
}
