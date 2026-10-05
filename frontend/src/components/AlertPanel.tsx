import type { Alert, Screen } from "../App";
import type { StormCell } from "./StormMap";

const ALERTS = [
  { id: "a1", severity: "Critical", type: "Lightning risk", district: "Villupuram District", probability: 91, time: "10:55–12:00 IST", color: "critical", cellId: "S-115" },
  { id: "a2", severity: "High", type: "Thunderstorm", district: "Chengalpattu District", probability: 87, time: "11:15–12:30 IST", color: "high", cellId: "S-104" },
  { id: "a3", severity: "High", type: "Thunderstorm", district: "Tiruvallur District", probability: 78, time: "11:00–12:00 IST", color: "high", cellId: "S-107" },
];

interface Props {
  setScreen: (s: Screen) => void;
  onViewOnMap: (cellId: string) => void;
  alerts: Alert[];
  stormCells: StormCell[];
}

export default function AlertPanel({ setScreen, onViewOnMap, alerts, stormCells }: Props) {
  const displayAlerts = alerts.length
    ? alerts.map((alert, index) => ({
        id: `${alert.district}-${alert.issued_at}`,
        severity: alert.risk_level === "HIGH" ? "High" : alert.risk_level === "MEDIUM" ? "Moderate" : "Low",
        type: "Lightning risk",
        district: `${alert.district}, ${alert.state}`,
        probability: Math.round(alert.probability * 100),
        time: alert.issued_at,
        color: alert.risk_level === "HIGH" ? "critical" : alert.risk_level === "MEDIUM" ? "high" : "normal",
        cellId: stormCells[index]?.id ?? stormCells[0]?.id,
      }))
    : ALERTS;

  return (
    <aside className="alerts-panel" aria-label="Active alerts">
      <div className="panel-heading">
        <div><h2>Active alerts (demo)</h2><p>{displayAlerts.length} warnings (prototype demo)</p></div>
        <span className="alert-count">{displayAlerts.length}</span>
      </div>
      <div className="alerts-list">
        {displayAlerts.map((alert) => (
          <article className={`alert-item ${alert.color}`} key={alert.id}>
            <div className="alert-item-top">
              <span className="severity">[demo] {alert.severity}</span>
              <span>{alert.time}</span>
            </div>
            <h3>{alert.type} (demo)</h3>
            <p>{alert.district}</p>
            <div className="alert-item-bottom">
              <strong>{alert.probability}% risk (uncalibrated)</strong>
              <button onClick={() => alert.cellId && onViewOnMap(alert.cellId)}>Show on map</button>
            </div>
          </article>
        ))}
      </div>
      <button className="view-all" onClick={() => setScreen("alerts")}>View all alerts</button>
    </aside>
  );
}
