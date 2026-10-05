interface Props {
  activeLayer: string;
  setActiveLayer: (l: string) => void;
  timeOffset: number;
  setTimeOffset: (t: number) => void;
}

const LAYERS = [
  { id: "storm", label: "Risk areas" },
  { id: "lightning", label: "Lightning" },
  { id: "radar", label: "Rain radar" },
  { id: "districts", label: "District boundaries" },
];

function formatForecastTime(minutes: number) {
  if (minutes === 0) {
    return "NOW";
  }

  if (minutes < 60) {
    return `+${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remaining = minutes % 60;

  if (remaining === 0) {
    return `+${hours} hr`;
  }

  return `+${hours} hr ${remaining} min`;
}

export default function Sidebar({
  activeLayer,
  setActiveLayer,
  timeOffset,
  setTimeOffset,
}: Props) {
  return (
    <aside
      className="map-sidebar"
      aria-label="Map options"
    >
      <div className="sidebar-section">
        <h2>Map view</h2>

        <div className="simple-options">
          {LAYERS.map((layer) => (
            <button
              key={layer.id}
              className={
                activeLayer === layer.id
                  ? "option-button selected"
                  : "option-button"
              }
              onClick={() =>
                setActiveLayer(layer.id)
              }
            >
              <span className="option-radio" />

              {layer.label}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-section forecast-section">
        <div className="forecast-heading">
          <h2>Forecast time</h2>

          <strong>
            {formatForecastTime(timeOffset)}
          </strong>
        </div>

        <input
          className="forecast-slider"
          type="range"
          min="0"
          max="180"
          step="15"
          value={timeOffset}
          onChange={(event) =>
            setTimeOffset(
              Number(event.target.value)
            )
          }
          aria-label="Forecast time from now to three hours"
        />

        <div className="forecast-labels">
          <span>NOW</span>
          <span>+3 HR</span>
        </div>

        <p className="forecast-hint">
          Drag to view the forecast in 15-minute
          intervals.
        </p>
      </div>

      <div className="sidebar-help">
        <strong>Emergency assistance</strong>

        <p>
          If you are in immediate danger, call the
          national emergency number.
        </p>

        <button
          onClick={() => window.open("tel:112")}
        >
          Call 112
        </button>
      </div>
    </aside>
  );
}