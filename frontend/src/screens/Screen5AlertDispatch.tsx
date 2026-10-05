import { useState } from "react";

const ALERT_TYPES = ["Thunderstorm", "Lightning", "Severe Weather"];
const SEVERITIES  = ["Advisory", "Watch", "Warning", "Severe Warning"];
const DISTRICTS   = ["Chengalpattu", "Tiruvallur", "Chennai", "Kanchipuram", "Vellore", "Ranipet", "Villupuram"];
const RECIPIENTS  = [
  "District Disaster Management Authority",
  "Emergency Response Teams",
  "Aviation Operations",
  "Power Utilities",
  "Public Alert System",
];

const SEV_COLOR: Record<string, string> = {
  "Advisory":       "var(--wx-low)",
  "Watch":          "var(--wx-mod)",
  "Warning":        "var(--wx-high)",
  "Severe Warning": "var(--wx-severe)",
};

const RADII = ["District-wide", "25 km", "50 km", "100 km"];

export default function Screen5AlertDispatch({ isDark: _isDark }: { isDark: boolean }) {
  const [alertType, setAlertType]   = useState("Thunderstorm");
  const [severity, setSeverity]     = useState("Warning");
  const [area, setArea]             = useState("Chengalpattu");
  const [radius, setRadius]         = useState(RADII[0]);
  const [recipients, setRecipients] = useState(new Set(RECIPIENTS));
  const [sent, setSent]             = useState(false);
  const [sending, setSending]       = useState(false);
  const [scheduled, setScheduled]   = useState(false);

  const toggle = (r: string) =>
    setRecipients((prev) => { const s = new Set(prev); s.has(r) ? s.delete(r) : s.add(r); return s; });

  const resetForm = () => {
    setAlertType("Thunderstorm");
    setSeverity("Warning");
    setArea("Chengalpattu");
    setRadius(RADII[0]);
    setRecipients(new Set(RECIPIENTS));
  };

  const handleSend = () => {
    setScheduled(false);
    setSending(true);
    setTimeout(() => { setSending(false); setSent(true); }, 1100);
  };

  const handleSchedule = () => {
    setScheduled(true);
    setSending(true);
    setTimeout(() => { setSending(false); setSent(true); }, 700);
  };

  if (sent) {
    return (
      <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "var(--bg-panel)", border: "1px solid var(--border-dim)",
          borderRadius: 6, padding: "40px 48px", textAlign: "center", maxWidth: 440,
        }}>
          <div style={{
            width: 48, height: 48, borderRadius: "50%",
            background: "color-mix(in srgb, var(--wx-low) 12%, transparent)", border: "1px solid color-mix(in srgb, var(--wx-low) 35%, transparent)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 16px",
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--wx-low)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 20, fontWeight: 700, color: "var(--wx-low)", marginBottom: 6 }}>
            {scheduled ? "Alert Scheduled" : "Alert Dispatched"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 18 }}>
            {severity} · {alertType} · {area} District · {radius}
          </div>
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "11px 14px", marginBottom: 18 }}>
            {[
              [scheduled ? "Scheduled for" : "Dispatched at",    "10:43:17 IST"],
              ["Recipients",       `${recipients.size} agencies`],
              ["Delivery status",  scheduled ? "PENDING" : "DELIVERED"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{k}</span>
                <span style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", color: "var(--wx-low)" }}>{v}</span>
              </div>
            ))}
          </div>
          <button onClick={() => { setSent(false); resetForm(); }} style={{
            background: "var(--accent-dim)", border: "1px solid var(--accent-border)",
            borderRadius: 6, color: "var(--accent)", fontSize: 12,
            fontFamily: "Manrope, sans-serif", fontWeight: 700, padding: "8px 22px", cursor: "pointer",
          }}>
            New alert
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>SCREEN 5</div>
        <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>Alert Center</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Create and dispatch operational weather alerts</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, maxWidth: 860 }}>
        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <FormBlock label="ALERT TYPE">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {ALERT_TYPES.map((t) => (
                <ToggleBtn key={t} active={alertType === t} onClick={() => setAlertType(t)}>{t}</ToggleBtn>
              ))}
            </div>
          </FormBlock>

          <FormBlock label="TARGET AREA">
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 9, color: "var(--text-muted)", marginBottom: 5 }}>District</div>
                <select value={area} onChange={(e) => setArea(e.target.value)} style={selectStyle}>
                  {DISTRICTS.map((d) => <option key={d}>{d}</option>)}
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 9, color: "var(--text-muted)", marginBottom: 5 }}>Radius</div>
                <select value={radius} onChange={(e) => setRadius(e.target.value)} style={selectStyle}>
                  {RADII.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
            </div>
          </FormBlock>

          <FormBlock label="SEVERITY">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
              {SEVERITIES.map((s) => {
                const c = SEV_COLOR[s];
                return (
                  <button key={s} onClick={() => setSeverity(s)} style={{
                    background: severity === s ? `color-mix(in srgb, ${c} 12%, transparent)` : "transparent",
                    border: `1px solid ${severity === s ? c : "var(--border-dim)"}`,
                    borderRadius: 3, padding: "4px 11px", cursor: "pointer",
                    color: severity === s ? c : "var(--text-secondary)", fontSize: 11,
                    fontFamily: "Inter, sans-serif",
                  }}>{s}</button>
                );
              })}
            </div>
          </FormBlock>
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <FormBlock label="RECIPIENTS">
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {RECIPIENTS.map((r) => (
                <label key={r} style={{ display: "flex", alignItems: "center", gap: 9, cursor: "pointer" }}>
                  <div onClick={() => toggle(r)} style={{
                    width: 14, height: 14, borderRadius: 2,
                    border: "1px solid var(--accent-border)",
                    background: recipients.has(r) ? "var(--accent)" : "transparent",
                    flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    {recipients.has(r) && (
                      <svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="#000" strokeWidth="2.5" strokeLinecap="round">
                        <polyline points="2 6 5 9 10 3" />
                      </svg>
                    )}
                  </div>
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{r}</span>
                </label>
              ))}
            </div>
          </FormBlock>

          <FormBlock label="MESSAGE PREVIEW">
            <div style={{
              fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.6,
              background: "var(--bg-navy)", border: "1px solid var(--border-dim)",
              borderRadius: 3, padding: "9px 11px",
            }}>
              StormSense Alert: High probability of severe {alertType.toLowerCase()} activity
              detected over {area} district{radius !== "District-wide" ? ` (${radius} radius)` : ""} between
              11:15–12:30 IST. Probability: 82%. Take appropriate precautions.
            </div>
          </FormBlock>

          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            <button onClick={handleSend} disabled={sending} style={{
              background: "color-mix(in srgb, var(--wx-severe) 10%, transparent)", border: "1px solid color-mix(in srgb, var(--wx-severe) 38%, transparent)",
              borderRadius: 6, color: "var(--wx-severe)", fontFamily: "Manrope, sans-serif",
              fontWeight: 700, fontSize: 14, padding: "10px", cursor: sending ? "wait" : "pointer",
              opacity: sending ? 0.6 : 1,
            }}>
              {sending && !scheduled ? "Dispatching…" : "Send alert"}
            </button>
            <div style={{ display: "flex", gap: 7 }}>
              <button onClick={handleSchedule} disabled={sending} style={{
                flex: 1, background: "transparent", border: "1px solid var(--border-dim)",
                borderRadius: 6, color: "var(--text-secondary)", fontFamily: "Manrope, sans-serif",
                fontWeight: 600, fontSize: 11.5, padding: "7px", cursor: sending ? "wait" : "pointer",
                opacity: sending ? 0.6 : 1,
              }}>
                {sending && scheduled ? "Scheduling…" : "Schedule"}
              </button>
              <button onClick={resetForm} style={{
                flex: 1, background: "transparent", border: "1px solid var(--border-dim)",
                borderRadius: 6, color: "var(--text-muted)", fontFamily: "Manrope, sans-serif",
                fontWeight: 600, fontSize: 11.5, padding: "7px", cursor: "pointer",
              }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FormBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5, padding: "14px" }}>
      <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 11 }}>{label}</div>
      {children}
    </div>
  );
}

function ToggleBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      background: active ? "var(--accent-dim)" : "transparent",
      border: `1px solid ${active ? "var(--accent-border)" : "var(--border-dim)"}`,
      borderRadius: 3, padding: "4px 11px", cursor: "pointer",
      color: active ? "var(--accent)" : "var(--text-secondary)", fontSize: 11,
      fontFamily: "Inter, sans-serif",
    }}>{children}</button>
  );
}

const selectStyle: React.CSSProperties = {
  width: "100%", background: "var(--bg-card)", border: "1px solid var(--border-dim)",
  borderRadius: 3, color: "var(--text-primary)", fontSize: 11, padding: "5px 7px",
  fontFamily: "Inter, sans-serif",
};
