import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { StormCell } from "../components/StormMap";
import type { Screen } from "../App";

interface Props {
  cell: StormCell | null;
  onBack: () => void;
  setScreen: (s: Screen) => void;
  isDark: boolean;
}

const DEFAULT_CELL: StormCell = {
  id: "S-104", lat: 12.52, lng: 79.8, probability: 87, lightningProb: 72,
  direction: "NE", speed: 32, eta: 42, intensity: "severe",
};

const SIGNALS = [
  { label: "Radar Echo Growth",          pct: 92, colorVar: "var(--accent)" },
  { label: "Satellite IR Cooling",       pct: 84, colorVar: "var(--wx-extreme)" },
  { label: "Lightning Density Increase", pct: 79, colorVar: "var(--wx-mod)" },
  { label: "Atmospheric Instability",    pct: 71, colorVar: "var(--wx-high)" },
];

const INTENSITY_COLOR_VAR: Record<string, string> = {
  low:      "var(--wx-low)",
  moderate: "var(--wx-high)",
  severe:   "var(--wx-severe)",
  extreme:  "var(--wx-extreme)",
};

export default function Screen2StormAnalysis({ cell, onBack, setScreen }: Props) {
  const c = cell ?? DEFAULT_CELL;
  const colorVar = INTENSITY_COLOR_VAR[c.intensity];
  const [interpretation, setInterpretation] = useState("Rapid radar echo growth combined with satellite cloud-top cooling and increasing lightning density indicates strengthening convection. Atmospheric instability supports continued intensification over the next 45–90 minutes.");
  const [analysisSource, setAnalysisSource] = useState("local-fallback");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/api/v1/nowcast/analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        cell_id: c.id,
        probability: c.probability,
        lightning_probability: c.lightningProb,
        intensity: c.intensity,
        direction: c.direction,
        speed: c.speed,
        eta: c.eta,
        latitude: c.lat,
        longitude: c.lng,
      }),
    })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Analysis unavailable")))
      .then((result: { source: string; interpretation: string }) => {
        setAnalysisSource(result.source);
        setInterpretation(result.interpretation);
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") setAnalysisSource("local-fallback");
      });
    return () => controller.abort();
  }, [c.id, c.probability, c.lightningProb, c.intensity, c.direction, c.speed, c.eta, c.lat, c.lng]);

  return (
    <div className="analysis-screen" style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Left — detailed interactive regional map view */}
      <div className="analysis-visual" style={{
        flex: 1, background: "var(--bg-navy)", position: "relative",
        display: "flex", alignItems: "center", justifyContent: "center",
        borderRight: "1px solid var(--border-dim)", height: "100%", width: "100%",
        overflow: "hidden",
      }}>
        <CellDetailMap cell={c} colorVar={colorVar} />

        <button onClick={onBack} style={{
          position: "absolute", top: 12, left: 12, zIndex: 1000,
          background: "var(--bg-panel)", border: "1px solid var(--border-dim)",
          borderRadius: 3, color: "var(--text-secondary)", fontSize: 11,
          padding: "5px 12px", cursor: "pointer", fontFamily: "Inter, sans-serif",
          boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
        }}>
          ← Live Command
        </button>

        <div style={{
          position: "absolute", bottom: 16, left: 16, zIndex: 1000,
          fontSize: 10, color: "var(--text-primary)", fontFamily: "JetBrains Mono, monospace",
          background: "rgba(15, 23, 42, 0.85)", padding: "4px 10px", borderRadius: 4,
          border: "1px solid var(--border-dim)", backdropFilter: "blur(4px)",
        }}>
          DETAILED REGION MAP · {c.lat.toFixed(2)}°N {c.lng.toFixed(2)}°E · ZOOM 13
        </div>
      </div>

      {/* Right panel */}
      <div className="analysis-panel" style={{
        width: 352, background: "var(--bg-panel)", overflowY: "auto",
        padding: "18px", display: "flex", flexDirection: "column", gap: 14,
        zIndex: 10,
      }}>
        <div>
          <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: 1.2, marginBottom: 3 }}>STORM CELL</div>
          <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 26, fontWeight: 700, color: "var(--text-primary)" }}>
            {c.id}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Detailed AI Analysis</div>
        </div>

        {/* Status */}
        <div style={{
          background: "var(--bg-card)", border: "1px solid var(--border-dim)",
          borderLeft: `3px solid ${colorVar}`, borderRadius: "0 4px 4px 0", padding: "13px",
        }}>
          <div style={{ fontSize: 9, letterSpacing: 1, color: "var(--text-muted)", marginBottom: 6 }}>CURRENT STATUS</div>
          <div style={{ fontFamily: "Manrope, sans-serif", fontSize: 16, fontWeight: 700, color: colorVar, marginBottom: 12 }}>
            INTENSIFYING
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 0" }}>
            {[
              { label: "Thunderstorm Prob.", value: `${c.probability}%`, colorVar: "var(--wx-severe)" },
              { label: "Lightning Prob.",    value: `${c.lightningProb}%`, colorVar: "var(--wx-mod)" },
              { label: "Intensity",          value: c.intensity.toUpperCase(), colorVar },
              { label: "Movement",           value: `${c.direction} · ${c.speed} km/h`, colorVar: "var(--accent)" },
              { label: "Estimated Arrival",  value: `${c.eta} min`, colorVar: "var(--wx-high)" },
              { label: "Grid Reference",     value: `${c.lat.toFixed(2)}N ${c.lng.toFixed(2)}E`, colorVar: "var(--text-secondary)" },
            ].map((item) => (
              <div key={item.label}>
                <div style={{ fontSize: 9, color: "var(--text-muted)", marginBottom: 2 }}>{item.label}</div>
                <div style={{ fontSize: 12, fontFamily: "JetBrains Mono, monospace", color: item.colorVar, fontWeight: 600 }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI signals */}
        <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "13px" }}>
          <div style={{ fontSize: 9, letterSpacing: 1, color: "var(--text-muted)", marginBottom: 12 }}>
            WHY STORMSENSE PREDICTS THIS EVENT
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {SIGNALS.map((sig) => (
              <div key={sig.label}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{sig.label}</span>
                  <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: sig.colorVar, fontWeight: 600 }}>
                    {sig.pct}%
                  </span>
                </div>
                <div style={{ height: 3, background: "var(--border-dim)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{
                    height: "100%", width: `${sig.pct}%`, borderRadius: 2,
                    background: sig.colorVar, transition: "width 0.4s ease",
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interpretation narrative */}
        <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-dim)", borderRadius: 4, padding: "13px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div style={{ fontSize: 9, letterSpacing: 1, color: "var(--text-muted)" }}>EXPLANATORY INTERPRETATION</div>
            <div style={{
              fontSize: 8,
              color: analysisSource === "grok" ? "var(--accent)" : "var(--text-muted)",
              fontFamily: "JetBrains Mono, monospace",
              fontWeight: 700,
              textTransform: "uppercase",
              background: analysisSource === "grok" ? "var(--accent-dim)" : "transparent",
              padding: analysisSource === "grok" ? "2px 6px" : "0",
              borderRadius: 3,
              border: analysisSource === "grok" ? "1px solid var(--accent-border)" : "none",
            }}>
              {analysisSource === "grok" ? "xAI Grok AI" : analysisSource === "groq" ? "Groq AI" : "Local AI"}
            </div>
          </div>
          <div style={{ fontSize: 11, lineHeight: 1.5, color: "var(--text-secondary)" }}>
            {interpretation}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <button onClick={() => setScreen("alerts")} style={{
            background: "var(--accent)", border: "none", borderRadius: 6,
            color: "#fff", fontFamily: "Manrope, sans-serif", fontWeight: 700,
            fontSize: 12, padding: "7px", cursor: "pointer",
          }}>
            Dispatch alert for {c.id}
          </button>
          <button onClick={() => setScreen("fusion")} style={{
            background: "var(--accent-dim)", border: "1px solid var(--accent-border)",
            borderRadius: 6, color: "var(--accent)", fontFamily: "Manrope, sans-serif",
            fontWeight: 600, fontSize: 12, padding: "7px", cursor: "pointer",
          }}>
            View in data fusion
          </button>
        </div>
      </div>
    </div>
  );
}

function CellDetailMap({ cell, colorVar }: { cell: StormCell; colorVar: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    if (mapRef.current) {
      mapRef.current.setView([cell.lat, cell.lng], 13);
      return;
    }

    const map = L.map(containerRef.current, {
      center: [cell.lat, cell.lng],
      zoom: 13,
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    // Impact zone concentric circles (5km core risk, 15km outer advisory)
    L.circle([cell.lat, cell.lng], {
      radius: 5000,
      color: "#b42318",
      fillColor: "#b42318",
      fillOpacity: 0.25,
      weight: 2,
    }).addTo(map);

    L.circle([cell.lat, cell.lng], {
      radius: 15000,
      color: "#d98a45",
      fillColor: "#d98a45",
      fillOpacity: 0.1,
      weight: 1.5,
      dashArray: "4, 6",
    }).addTo(map);

    // High detail storm cell marker
    const icon = L.divIcon({
      className: "storm-cell-detail-marker",
      html: `
        <div style="
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: #991b1b44;
          border: 3px solid #b42318;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 14px #b42318aa;
        ">
          <div style="width: 6px; height: 6px; border-radius: 50%; background: #b42318;"></div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });

    const marker = L.marker([cell.lat, cell.lng], { icon }).addTo(map);
    marker
      .bindPopup(
        `
        <div style="font-family: Inter, sans-serif; font-size: 12px; color: #111;">
          <strong style="font-size: 14px;">Storm Cell ${cell.id}</strong><br/>
          Intensity: <strong style="color: #b42318;">${cell.intensity.toUpperCase()}</strong><br/>
          Probability: <strong>${cell.probability}%</strong><br/>
          Speed: <strong>${cell.speed} km/h ${cell.direction}</strong><br/>
          ETA: <strong>${cell.eta} min</strong>
        </div>
      `
      )
      .openPopup();

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [cell.lat, cell.lng, cell.id, cell.intensity, cell.probability, cell.speed, cell.direction]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", position: "absolute", inset: 0 }}
    />
  );
}
