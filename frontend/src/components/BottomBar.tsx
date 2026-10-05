const METRICS = [
  { label: "Rainfall", value: "72 mm", sub: "Last 1 hour", tone: "warning" },
  { label: "Active alerts", value: "3", sub: "2 high priority", tone: "critical" },
  { label: "Risk zones", value: "5", sub: "Under monitoring", tone: "warning" },
  { label: "Sensors", value: "98%", sub: "Reporting normally", tone: "normal" },
];

export default function BottomBar() {
  return (
    <section className="metrics-bar" aria-label="District summary">
      {METRICS.map((metric) => (
        <div className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <div><strong className={metric.tone}>{metric.value}</strong><small>{metric.sub}</small></div>
        </div>
      ))}
    </section>
  );
}
