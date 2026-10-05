import { useEffect, useState } from "react";
import TopNav from "./components/TopNav";
import Sidebar from "./components/Sidebar";
import AlertPanel from "./components/AlertPanel";
import AlertBanner from "./components/AlertBanner";
import BottomBar from "./components/BottomBar";
import StormMap, { cellsFromHeatmap, STORM_CELLS } from "./components/StormMap";

import Screen2StormAnalysis from "./screens/Screen2StormAnalysis";
import Screen3DataFusion from "./screens/Screen3DataFusion";
import Screen4Forecast from "./screens/Screen4Forecast";
import Screen5AlertDispatch from "./screens/Screen5AlertDispatch";
import Screen6Performance from "./screens/Screen6Performance";
import Screen7SystemStatus from "./screens/Screen7SystemStatus";

import type { StormCell } from "./components/StormMap";

type RiskLevel = "HIGH" | "MEDIUM" | "LOW";
export type Heatmap = {
  type: "FeatureCollection";
  features: Array<{
    geometry: { coordinates: number[][][] };
    properties: { lightning_probability: number; risk_level: RiskLevel; timestamp_offset: string; source: string };
  }>;
};
export type Alert = { district: string; state: string; risk_level: RiskLevel; probability: number; issued_at: string };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type Screen =
  | "live"
  | "analysis"
  | "fusion"
  | "forecast"
  | "alerts"
  | "performance"
  | "system";

const NAV_ITEMS: { id: Screen; label: string }[] = [
  { id: "live", label: "Overview" },
  { id: "analysis", label: "Storm analysis" },
  { id: "forecast", label: "Forecast" },
  { id: "alerts", label: "Alerts" },
  { id: "fusion", label: "Data sources" },
  { id: "performance", label: "Performance" },
  { id: "system", label: "System status" },
];

export default function App() {
  const [screen, setScreen] = useState<Screen>("live");

  const [selectedCell, setSelectedCell] =
    useState<StormCell | null>(null);

  const [activeLayer, setActiveLayer] = useState("storm");

  /*
   * Forecast is stored in MINUTES.
   *
   * 0    = NOW
   * 15   = +15 min
   * 30   = +30 min
   * ...
   * 180  = +3 hr
   */
  const [timeOffset, setTimeOffset] = useState(0);

  const [bannerDismissed, setBannerDismissed] =
    useState(false);

  const [isDark, setIsDark] = useState(false);
  const [heatmap, setHeatmap] = useState<Heatmap | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  /*
   * Apply the theme to the root app.
   */
  useEffect(() => {
    document.documentElement.setAttribute(
      "data-theme",
      isDark ? "dark" : "light"
    );
  }, [isDark]);

  useEffect(() => {
    const controller = new AbortController();
    // The model begins at +15 min; the UI's NOW position uses that first available forecast.
    const forecastOffset = timeOffset || 15;
    Promise.all([
      fetch(`${API_URL}/api/v1/nowcast/heatmap?time_offset_mins=${forecastOffset}`, { signal: controller.signal }),
      fetch(`${API_URL}/api/v1/alerts`, { signal: controller.signal }),
    ])
      .then(async ([heatmapResponse, alertsResponse]) => {
        if (!heatmapResponse.ok || !alertsResponse.ok) throw new Error("API request failed");
        setHeatmap(await heatmapResponse.json());
        setAlerts(await alertsResponse.json());
      })
      .catch((error: unknown) => {
        if ((error as Error).name !== "AbortError") {
          setHeatmap(null);
          setAlerts([]);
        }
      });
    return () => controller.abort();
  }, [timeOffset]);

  const stormCells = heatmap ? cellsFromHeatmap(heatmap) : STORM_CELLS;

  const handleCellClick = (cell: StormCell) => {
    setSelectedCell(cell);
    setScreen("analysis");
  };

  const handleViewCellOnMap = (cellId: string) => {
    const cell =
      stormCells.find((c) => c.id === cellId) ?? null;

    setSelectedCell(cell);
    setScreen("live");
  };

  return (
    <div
      className={`app-shell ${
        isDark ? "theme-dark" : "theme-light"
      }`}
    >
      <TopNav
        screen={screen}
        setScreen={setScreen}
        navItems={NAV_ITEMS}
        isDark={isDark}
        setIsDark={setIsDark}
      />

      {screen === "live" && !bannerDismissed && (
        <AlertBanner
          onDismiss={() => setBannerDismissed(true)}
          onViewDetails={() => setScreen("alerts")}
        />
      )}

      <div
        style={{
          flex: 1,
          overflow: "hidden",
          position: "relative",
        }}
      >
        {screen === "live" && (
          <div
            style={{
              display: "flex",
              height: "100%",
              overflow: "hidden",
            }}
          >
            <Sidebar
              activeLayer={activeLayer}
              setActiveLayer={setActiveLayer}
              timeOffset={timeOffset}
              setTimeOffset={setTimeOffset}
            />

            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                minWidth: 0,
              }}
            >
              <div
                style={{
                  flex: 1,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                <StormMap
                  activeLayer={activeLayer}
                  timeOffset={timeOffset}
                  onCellClick={handleCellClick}
                  selectedCell={selectedCell?.id ?? null}
                  isDark={isDark}
                  heatmap={heatmap}
                  stormCells={stormCells}
                />
              </div>

              <BottomBar />
            </div>

            <AlertPanel
              setScreen={setScreen}
              onViewOnMap={handleViewCellOnMap}
              alerts={alerts}
              stormCells={stormCells}
            />
          </div>
        )}

        {screen === "analysis" && (
          <Screen2StormAnalysis
            cell={selectedCell}
            onBack={() => setScreen("live")}
            setScreen={setScreen}
            isDark={isDark}
            activeLayer={activeLayer}
            timeOffset={timeOffset}
            heatmap={heatmap}
            stormCells={stormCells}
            onCellClick={handleCellClick}
          />
        )}

        {screen === "fusion" && (
          <Screen3DataFusion isDark={isDark} />
        )}

        {screen === "forecast" && (
          <Screen4Forecast isDark={isDark} />
        )}

        {screen === "alerts" && (
          <Screen5AlertDispatch isDark={isDark} />
        )}

        {screen === "performance" && (
          <Screen6Performance isDark={isDark} />
        )}

        {screen === "system" && (
          <Screen7SystemStatus isDark={isDark} />
        )}
      </div>
    </div>
  );
}
