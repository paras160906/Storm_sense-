const SYSTEMS = [
  { name: "DWR Radar",         status: "Online",  lastUpdate: "10:40 IST",      latency: "8 sec"  },
  { name: "INSAT-3D/3DR",      status: "Online",  lastUpdate: "10:39 IST",      latency: "12 sec" },
  { name: "Lightning Network", status: "Online",  lastUpdate: "10:41 IST",      latency: "3 sec"  },
  { name: "NWP Model",         status: "Online",  lastUpdate: "Latest 06Z",     latency: "—"      },
  { name: "Model Inference",   status: "Healthy", lastUpdate: "Continuous",     latency: "18 sec" },
  { name: "API Gateway",       status: "Healthy", lastUpdate: "—",              latency: "< 5 ms" },
  { name: "Database",          status: "Healthy", lastUpdate: "—",              latency: "2 ms"   },
];

const UPTIME = [
  { label: "DWR",   pct: 99.7 },
  { label: "SAT",   pct: 99.5 },
  { label: "LTX",   pct: 98.4 },
  { label: "NWP",   pct: 99.1 },
  { label: "MODEL", pct: 99.8 },
];

const INGEST = [
  { label: "Radar volumes / hr",    value: "4"                },
  { label: "Satellite passes / hr", value: "2"                },
  { label: "Lightning msgs / min",  value: "247"              },
  { label: "NWP cycles / day",      value: "4 (00/06/12/18Z)" },
  { label: "Alert delivery rate",   value: "100%"             },
];

export default function Screen7SystemStatus({ isDark: _isDark }: { isDark: boolean }) {
  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>SCREEN 7</div>
        <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>System & Data Health</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          Real-time operational status of all data ingestion and processing systems
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 18 }}>
        {/* Left */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 11 }}>
            {SYSTEMS.map((sys) => (
              <div key={sys.name} style={{
                background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: 5,
                padding: "13px", display: "flex", alignItems: "flex-start", gap: 10,
              }}>
                <div style={{
                  width: 8, height: 8, borderRadius: "50%", background: "var(--wx-low)",
                  marginTop: 4, flexShrink: 0, boxShadow: "0 0 6px var(--wx-low)",
                }} />
                <div>
                  <div style={{ fontFamily: "Manrope, sans-serif", fontWeight: 700, fontSize: 13, color: "var(--text-primary)", marginBottom: 3 }}>
                    {sys.name}
                  </div>
                  <div style={{ fontSize: 9, fontFamily: "JetBrains Mono, monospace", color: "var(--wx-low)", marginBottom: 7, letterSpacing: 0.3 }}>
                    {sys.status.toUpperCase()}
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    {sys.lastUpdate !== "—" && (
                      <div>
                        <div style={{ fontSize: 8, color: "var(--text-muted)" }}>Last update</div>
                        <div style={{ fontSize: 9, fontFamily: "JetBrains Mono, monospace", color: "var(--text-secondary)" }}>{sys.lastUpdate}</div>
                      </div>
                    )}
                    {sys.latency !== "—" && (
                      <div>
                        <div style={{ fontSize: 8, color: "var(--text-muted)" }}>Latency</div>
                        <div style={{ fontSize: 9, fontFamily: "JetBrains Mono, monospace", color: "var(--text-secondary)" }}>{sys.latency}</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Uptime */}
          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5, padding: "14px" }}>
            <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 12 }}>30-DAY UPTIME</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
              {UPTIME.map((u) => {
                const barColor = u.pct > 99 ? "var(--wx-low)" : u.pct > 98 ? "var(--wx-mod)" : "var(--wx-severe)";
                return (
                  <div key={u.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "var(--text-muted)", width: 42 }}>{u.label}</span>
                    <div style={{ flex: 1, height: 4, background: "var(--border-dim)", borderRadius: 3 }}>
                      <div style={{ height: "100%", borderRadius: 3, width: `${u.pct}%`, background: barColor }} />
                    </div>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: barColor, width: 38, textAlign: "right" }}>
                      {u.pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Forecast cycle */}
          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5, padding: "16px" }}>
            <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 14 }}>FORECAST CYCLE</div>
            {[
              { label: "Current Cycle",    value: "10:45 IST",      colorVar: "var(--accent)" },
              { label: "Next Cycle",       value: "11:00 IST",      colorVar: "var(--wx-mod)" },
              { label: "Update Frequency", value: "Every 15 min",   colorVar: "var(--text-secondary)" },
              { label: "Cycle Duration",   value: "~12 sec",        colorVar: "var(--text-secondary)" },
            ].map((item) => (
              <div key={item.label} style={{
                display: "flex", justifyContent: "space-between",
                marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid var(--border-dim)",
              }}>
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{item.label}</span>
                <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: item.colorVar, fontWeight: 600 }}>
                  {item.value}
                </span>
              </div>
            ))}
            <div style={{
              background: "var(--accent-dim)", border: "1px solid var(--accent-border)",
              borderRadius: 3, padding: "9px 11px", textAlign: "center",
            }}>
              <div style={{ fontSize: 9, color: "var(--accent)", letterSpacing: 0.6, marginBottom: 3 }}>NEXT CYCLE IN</div>
              <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 26, color: "var(--accent)", fontWeight: 700 }}>
                11:52
              </div>
            </div>
          </div>

          {/* Ingest */}
          <div style={{ background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5, padding: "16px", flex: 1 }}>
            <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 12 }}>DATA INGEST STATUS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
              {INGEST.map((item) => (
                <div key={item.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{item.label}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "var(--text-secondary)" }}>
                      {item.value}
                    </span>
                    <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--wx-low)" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
