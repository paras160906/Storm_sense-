interface Props {
  onDismiss: () => void;
  onViewDetails: () => void;
}

export default function AlertBanner({ onDismiss, onViewDetails }: Props) {
  return (
    <section className="main-alert" aria-label="Current weather warning">
      <div className="alert-symbol" aria-hidden="true">!</div>
      <div className="alert-copy">
        <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
          <span style={{ background: "#d97706", color: "#fff", fontSize: "10px", fontWeight: "bold", padding: "1px 6px", borderRadius: "3px" }}>demo</span>
          <span style={{ background: "#4b5563", color: "#fff", fontSize: "10px", fontWeight: "bold", padding: "1px 6px", borderRadius: "3px" }}>PROTOTYPE: model not validated</span>
        </div>
        <div className="alert-heading">Flash flood warning (Demo)</div>
        <p>Heavy rainfall is expected in the monitored area at lead steps (+15, +30, +60, +120, +180 min).</p>
      </div>
      <div className="alert-meta">Severity: <strong>High</strong></div>
      <button className="alert-action" onClick={onViewDetails}>View full alert</button>
      <button className="alert-dismiss" onClick={onDismiss} aria-label="Dismiss warning">×</button>
    </section>
  );
}
