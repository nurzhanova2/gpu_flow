export default function Card({ children, className = "", muted = false }) {
  return (
    <section className={`panel-card ${muted ? "panel-card-muted" : ""} ${className}`.trim()}>
      {children}
    </section>
  );
}
