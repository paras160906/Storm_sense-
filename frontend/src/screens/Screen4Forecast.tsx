import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";

const FORECAST_DATA = [
  { time: "10:45", thunder: 58, lightning: 45 },
  { time: "11:00", thunder: 63, lightning: 51 },
  { time: "11:15", thunder: 69, lightning: 57 },
  { time: "11:30", thunder: 78, lightning: 66 },
  { time: "11:45", thunder: 85, lightning: 74 },
  { time: "12:00", thunder: 89, lightning: 79 },
  { time: "12:15", thunder: 87, lightning: 76 },
  { time: "12:30", thunder: 82, lightning: 70 },
  { time: "12:45", thunder: 73, lightning: 60 },
  { time: "13:00", thunder: 61, lightning: 48 },
  { time: "13:15", thunder: 48, lightning: 36 },
];

const SNAPSHOTS = [
  {
    label: "NOW",   time: "10:42", risk: "Moderate",
    colorVar: "var(--wx-low)",
    desc: "7 active cells in observation area. Developing convection over Villupuram. Low-to-moderate risk across Kanchipuram and Ranipet.",
  },
  {
    label: "+1 HR", time: "11:42", risk: "High",
    colorVar: "var(--wx-high)",
    desc: "Rapid intensification of cells S-104, S-115. High risk expanding over Chengalpattu and southern Chennai. Elevated lightning hazard.",
  },
  {
    label: "+2 HR", time: "12:42", risk: "Severe",
    colorVar: "var(--wx-severe)",
    desc: "Peak storm activity. Severe thunderstorm and lightning risk over Chennai metropolitan area. Cells consolidating into squall line.",
  },
  {
    label: "+3 HR", time: "13:42", risk: "Moderate",
    colorVar: "var(--wx-mod)",
    desc: "Gradual weakening as systems move northeast into Bay of Bengal. Residual lightning risk over coastal zones. Risk subsiding.",
  },
];

export default function Screen4Forecast({ isDark: _isDark }: { isDark: boolean }) {
  const gridColor = "var(--border-dim)";
  const tickColor = "var(--text-muted)";
  const tooltipBg = "var(--bg-panel)";

  return (
    <div style={{ height: "100%", overflowY: "auto", padding: "18px 22px" }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>SCREEN 4</div>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>3-Hour Forecast</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Probabilistic nowcast: 10:45 → 13:15 IST</div>
          </div>
          <div style={{
            background: "color-mix(in srgb, var(--wx-severe) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--wx-severe) 30%, transparent)",
            borderRadius: 3, padding: "7px 14px", textAlign: "center",
          }}>
            <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 0.8 }}>PEAK RISK WINDOW</div>
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 15, color: "var(--wx-severe)", fontWeight: 700, marginTop: 2 }}>
              11:30–12:30 IST
            </div>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{
        background: "var(--bg-panel)", border: "1px solid var(--border-dim)", borderRadius: 5,
        padding: "16px", marginBottom: 18,
      }}>
        <div style={{ fontSize: 9, letterSpacing: 1.2, color: "var(--text-muted)", marginBottom: 14 }}>PROBABILITY TIMELINE</div>
        <ResponsiveContainer width="100%" height={210}>
          <LineChart data={FORECAST_DATA} margin={{ top: 5, right: 16, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis
              dataKey="time"
              tick={{ fill: tickColor, fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              axisLine={{ stroke: gridColor }} tickLine={false}
            />
            <YAxis
              tick={{ fill: tickColor, fontSize: 10, fontFamily: "JetBrains Mono, monospace" }}
              axisLine={false} tickLine={false} domain={[0, 100]}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              contentStyle={{ background: tooltipBg, border: "1px solid var(--border-bright)", borderRadius: 3, fontSize: 11, fontFamily: "JetBrains Mono, monospace" }}
              labelStyle={{ color: "var(--text-secondary)" }}
              formatter={(val) => [`${val}%`]}
            />
            <Legend
              formatter={(val) => val === "thunder" ? "Thunderstorm Prob." : "Lightning Prob."}
              wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }}
            />
            <ReferenceLine x="11:30" stroke="var(--wx-severe)" strokeOpacity={0.35} strokeDasharray="4 4" />
            <ReferenceLine x="12:30" stroke="var(--wx-severe)" strokeOpacity={0.35} strokeDasharray="4 4" />
            <Line type="monotone" dataKey="thunder"  stroke="var(--wx-severe)" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="lightning" stroke="var(--wx-mod)"   strokeWidth={2} dot={false} strokeDasharray="6 3" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Snapshots */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 11 }}>
        {SNAPSHOTS.map((snap) => (
          <div key={snap.label} style={{
            background: "var(--bg-card)", border: "1px solid var(--border-dim)",
            borderTop: `3px solid ${snap.colorVar}`, borderRadius: "0 0 4px 4px", padding: "12px",
          }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 13, fontWeight: 700, color: snap.colorVar }}>
                {snap.label}
              </span>
              <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
                {snap.time}
              </span>
            </div>
            <div style={{
              display: "inline-block", border: `1px solid ${snap.colorVar}44`,
              borderRadius: 2, padding: "1px 7px", fontSize: 8, color: snap.colorVar,
              fontFamily: "JetBrains Mono, monospace", marginBottom: 7, letterSpacing: 0.4,
            }}>
              {snap.risk.toUpperCase()}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.55 }}>{snap.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
