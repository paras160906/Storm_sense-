const SOURCES = [
  {
    name: "Doppler Weather Radar", code: "DWR",
    metrics: [
      { label: "Radar Reflectivity", value: "48 dBZ",          colorVar: "var(--wx-high)"   },
      { label: "Echo Growth",        value: "+23% / 15 min",   colorVar: "var(--wx-severe)" },
      { label: "Coverage",           value: "84%",             colorVar: "var(--wx-low)"    },
    ],
    weight: 92,
  },
  {
    name: "INSAT-3D/3DR", code: "SAT",
    metrics: [
      { label: "Cloud Top Temperature", value: "−62°C",   colorVar: "var(--accent)"    },
      { label: "Cooling Rate",          value: "−4.2°C/15 min", colorVar: "var(--wx-extreme)" },
      { label: "Coverage",              value: "100%",              colorVar: "var(--wx-low)"    },
    ],
    weight: 84,
  },
  {
    name: "Lightning Sensors", code: "LTX",
    metrics: [
      { label: "Strikes / 15 min", value: "247",   colorVar: "var(--wx-mod)"    },
      { label: "Strike Density",   value: "+31%",  colorVar: "var(--wx-high)"   },
      { label: "Coverage",         value: "91%",   colorVar: "var(--wx-low)"    },
    ],
    weight: 79,
  },
  {
    name: "NWP Model", code: "NWP",
    metrics: [
      { label: "CAPE",       value: "1840 J/kg", colorVar: "var(--wx-severe)" },
      { label: "CIN",        value: "42 J/kg",   colorVar: "var(--wx-mod)"    },
      { label: "Wind Shear", value: "18 m/s",    colorVar: "var(--accent)"    },
    ],
    weight: 71,
  },
];

export default function Screen3DataFusion({ isDark: _isDark }: { isDark: boolean }) {
  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>SCREEN 3</div>
        <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>Data Fusion</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          Four real-time sources contributing to the current forecast
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        {SOURCES.map((src) => (
          <div key={src.code} style={{
            background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: 5,
            padding: "14px", position: "relative", overflow: "hidden",
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 14 }}>
              <div style={{
                width: 30, height: 30, borderRadius: 4, background: "var(--bg-panel)",
                border: "1px solid var(--border-dim)", display: "flex", alignItems: "center",
                justifyContent: "center", flexShrink: 0,
              }}>
                <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 9, color: "var(--accent)", fontWeight: 700 }}>
                  {src.code}
                </span>
              </div>
              <div>
                <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>
                  {src.name}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--wx-low)" }} />
                  <span style={{ fontSize: 9, color: "var(--wx-low)", fontFamily: "JetBrains Mono, monospace" }}>ONLINE</span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 13 }}>
              {src.metrics.map((m) => (
                <div key={m.label}>
                  <div style={{ fontSize: 9, color: "var(--text-muted)", marginBottom: 2 }}>{m.label}</div>
                  <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 14, fontWeight: 600, color: m.colorVar }}>
                    {m.value}
                  </div>
                </div>
              ))}
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ fontSize: 9, color: "var(--text-muted)" }}>Model contribution</span>
                <span style={{ fontSize: 9, fontFamily: "JetBrains Mono, monospace", color: "var(--accent)" }}>{src.weight}%</span>
              </div>
              <div style={{ height: 3, background: "var(--border-dim)", borderRadius: 2 }}>
                <div style={{ height: "100%", width: `${src.weight}%`, borderRadius: 2, background: "var(--accent)", opacity: 0.85 }} />
              </div>
            </div>

            <div style={{
              position: "absolute", bottom: -6, right: 6,
              fontFamily: "JetBrains Mono, monospace", fontSize: 38, fontWeight: 800,
              color: "var(--border-dim)", lineHeight: 1, pointerEvents: "none",
            }}>{src.code}</div>
          </div>
        ))}
      </div>

      {/* Fusion diagram */}
      <div style={{
        background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5, padding: "18px 22px",
      }}>
        <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 14 }}>FUSION ARCHITECTURE</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexWrap: "wrap", gap: 0 }}>
          {SOURCES.map((src, i) => (
            <div key={src.code} style={{ display: "flex", alignItems: "center" }}>
              <div style={{
                background: "var(--bg-card)", border: "1px solid var(--border-bright)",
                borderRadius: 3, padding: "7px 13px", textAlign: "center",
              }}>
                <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, color: "var(--accent)" }}>{src.code}</div>
                <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>{src.name.split(" ")[0]}</div>
              </div>
              {i < SOURCES.length - 1 && (
                <div style={{ fontSize: 14, color: "var(--text-muted)", margin: "0 7px" }}>+</div>
              )}
            </div>
          ))}

          <div style={{ fontSize: 18, color: "var(--accent)", margin: "0 14px" }}>→</div>

          <div style={{
            background: "var(--accent-dim)", border: "1px solid var(--accent-border)",
            borderRadius: 5, padding: "10px 18px", textAlign: "center",
          }}>
            <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 700, color: "var(--accent)" }}>
              StormSense Fusion Model
            </div>
            <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2, letterSpacing: 0.3 }}>AI · MULTI-SOURCE</div>
          </div>

          <div style={{ fontSize: 18, color: "var(--accent)", margin: "0 14px" }}>→</div>

          <div style={{
            background: "color-mix(in srgb, var(--wx-severe) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--wx-severe) 30%, transparent)",
            borderRadius: 5, padding: "10px 18px", textAlign: "center",
          }}>
            <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 13, fontWeight: 700, color: "var(--wx-severe)" }}>
              3-Hour Risk Forecast
            </div>
            <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2, letterSpacing: 0.3 }}>GRID · DISTRICT</div>
          </div>
        </div>
      </div>
    </div>
  );
}
