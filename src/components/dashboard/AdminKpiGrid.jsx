import StatCard from "../ui/StatCard";

export default function AdminKpiGrid({ items }) {
  return (
    <section className="stats-grid stats-grid-admin">
      {items.map((item) => (
        <StatCard key={item.id} label={item.label} value={item.value} hint={item.hint} tone={item.tone} />
      ))}
    </section>
  );
}
