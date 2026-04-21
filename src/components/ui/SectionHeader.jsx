export default function SectionHeader({ title, subtitle, right }) {
  return (
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {right ? <div className="section-header-right">{right}</div> : null}
    </div>
  );
}
