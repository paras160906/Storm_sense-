import {
  useEffect,
  useRef,
  useCallback,
} from "react";

import L from "leaflet";
import "leaflet.heat";
import type { Heatmap } from "../App";

export interface StormCell {
  id: string;
  lat: number;
  lng: number;
  probability: number;
  lightningProb: number;
  direction: string;
  speed: number;
  eta: number;
  intensity:
    | "low"
    | "moderate"
    | "severe"
    | "extreme";
}

interface Props {
  activeLayer: string;
  timeOffset: number;
  onCellClick: (cell: StormCell) => void;
  selectedCell: string | null;
  isDark: boolean;
  heatmap: Heatmap | null;
  stormCells: StormCell[];
}

/* -------------------------------------------------------------------------- */
/* Storm cells                                                                */
/* -------------------------------------------------------------------------- */

export const STORM_CELLS: StormCell[] = [
  {
    id: "S-115",
    lat: 11.9,
    lng: 79.9,
    probability: 91,
    lightningProb: 84,
    direction: "N",
    speed: 35,
    eta: 28,
    intensity: "extreme",
  },

  {
    id: "S-104",
    lat: 12.52,
    lng: 79.8,
    probability: 87,
    lightningProb: 72,
    direction: "NE",
    speed: 32,
    eta: 42,
    intensity: "severe",
  },

  {
    id: "S-107",
    lat: 12.1,
    lng: 79.4,
    probability: 74,
    lightningProb: 61,
    direction: "NE",
    speed: 28,
    eta: 68,
    intensity: "severe",
  },

  {
    id: "S-112",
    lat: 12.78,
    lng: 79.2,
    probability: 58,
    lightningProb: 44,
    direction: "E",
    speed: 22,
    eta: 95,
    intensity: "moderate",
  },

  {
    id: "S-118",
    lat: 13.1,
    lng: 79.6,
    probability: 51,
    lightningProb: 36,
    direction: "SE",
    speed: 18,
    eta: 120,
    intensity: "moderate",
  },

  {
    id: "S-121",
    lat: 12.4,
    lng: 80.1,
    probability: 32,
    lightningProb: 19,
    direction: "NW",
    speed: 14,
    eta: 155,
    intensity: "low",
  },

  {
    id: "S-123",
    lat: 13.4,
    lng: 79.1,
    probability: 22,
    lightningProb: 12,
    direction: "E",
    speed: 16,
    eta: 185,
    intensity: "low",
  },
];

function intensityFor(probability: number): StormCell["intensity"] {
  if (probability >= 70) return "extreme";
  if (probability >= 50) return "severe";
  if (probability >= 30) return "moderate";
  return "low";
}

function featureCenter(feature: Heatmap["features"][number]) {
  const points = feature.geometry.coordinates[0];
  const count = Math.max(points.length - 1, 1);
  const [lng, lat] = points.slice(0, count).reduce(
    ([sumLng, sumLat], [pointLng, pointLat]) => [sumLng + pointLng, sumLat + pointLat],
    [0, 0],
  );
  return [lat / count, lng / count] as [number, number];
}

export function cellsFromHeatmap(heatmap: Heatmap): StormCell[] {
  return [...heatmap.features]
    .sort((a, b) => b.properties.lightning_probability - a.properties.lightning_probability)
    .slice(0, 7)
    .map((feature, index) => {
      const probability = Math.round(feature.properties.lightning_probability * 100);
      const [lat, lng] = featureCenter(feature);
      return {
        id: `M-${String(index + 1).padStart(3, "0")}`,
        lat,
        lng,
        probability,
        lightningProb: probability,
        direction: "—",
        speed: 0,
        eta: Number(feature.properties.timestamp_offset.replace(/\D/g, "")) || 15,
        intensity: intensityFor(probability),
      };
    });
}

function heatmapPoints(heatmap: Heatmap): [number, number, number][] {
  const threshold = 0.08;
  const features = heatmap.features.filter(
    (feature) => feature.properties.lightning_probability > threshold
  );
  if (!features.length) return [];

  const maxProb = Math.max(
    ...features.map((f) => f.properties.lightning_probability)
  );
  const scale = maxProb > 0 ? Math.min(1.0 / maxProb, 2.2) : 1.0;

  return features.map((feature) => {
    const [lat, lng] = featureCenter(feature);
    const scaledIntensity = Math.min(
      (feature.properties.lightning_probability - threshold) * scale,
      1.0
    );
    return [lat, lng, scaledIntensity];
  });
}

/* -------------------------------------------------------------------------- */
/* Base heatmap data                                                          */
/* -------------------------------------------------------------------------- */

const BASE_LOW: [
  number,
  number,
  number
][] = [
  [14.0, 80.0, 0.12],
  [13.9, 79.5, 0.10],
  [13.8, 79.8, 0.14],
  [13.7, 80.1, 0.11],
  [14.1, 79.2, 0.09],
  [13.6, 79.3, 0.13],
  [13.5, 80.2, 0.10],
  [14.2, 79.7, 0.08],
  [11.6, 79.5, 0.12],
  [11.5, 79.8, 0.10],
  [11.7, 80.1, 0.09],
  [11.4, 79.2, 0.11],
  [12.0, 78.8, 0.12],
  [11.8, 78.6, 0.10],
  [12.2, 78.5, 0.09],
  [13.2, 78.9, 0.11],
  [13.5, 78.7, 0.09],
];

const BASE_MOD: [
  number,
  number,
  number
][] = [
  [12.93, 79.32, 0.38],
  [12.88, 79.26, 0.35],
  [12.99, 79.38, 0.33],
  [12.85, 79.19, 0.30],
  [13.0, 79.14, 0.28],

  [12.83, 79.7, 0.45],
  [12.78, 79.63, 0.42],
  [12.88, 79.77, 0.40],
  [12.73, 79.56, 0.36],
  [12.95, 79.82, 0.32],

  [12.4, 80.1, 0.30],
  [12.35, 80.05, 0.27],
  [12.45, 80.15, 0.25],

  [13.4, 79.1, 0.22],
  [13.35, 79.05, 0.20],
  [13.45, 79.15, 0.18],

  [13.1, 79.6, 0.48],
  [13.05, 79.55, 0.44],
  [13.15, 79.65, 0.42],
];

/* -------------------------------------------------------------------------- */
/* Heatmap zones                                                              */
/* -------------------------------------------------------------------------- */

const HEATMAP_ZONES: Record<
  number,
  [number, number, number][]
> = {
  0: [
    ...BASE_LOW,
    ...BASE_MOD,

    [12.52, 79.8, 1.0],
    [12.48, 79.74, 0.95],
    [12.57, 79.86, 0.91],
    [12.43, 79.68, 0.86],
    [12.62, 79.93, 0.80],
    [12.38, 79.57, 0.72],
    [12.60, 80.02, 0.64],

    [12.1, 79.4, 0.78],
    [12.05, 79.33, 0.72],
    [12.15, 79.46, 0.68],
    [12.0, 79.26, 0.62],
    [12.22, 79.52, 0.57],

    [11.9, 79.9, 1.0],
    [11.85, 79.83, 0.95],
    [11.95, 79.97, 0.91],
    [11.8, 79.76, 0.85],
    [12.0, 80.04, 0.78],

    [13.15, 79.9, 0.82],
    [13.1, 79.83, 0.77],
    [13.2, 79.97, 0.73],
    [13.05, 79.76, 0.68],
    [13.25, 80.03, 0.62],

    [13.08, 80.27, 0.52],
    [13.05, 80.21, 0.47],
    [13.12, 80.32, 0.44],
  ],

  30: [
    ...BASE_LOW,
    ...BASE_MOD,

    [12.6, 80.02, 1.0],
    [12.55, 79.93, 0.95],
    [12.66, 80.08, 0.90],
    [12.5, 79.87, 0.87],
    [12.72, 80.13, 0.81],

    [13.2, 80.0, 0.84],
    [13.15, 79.94, 0.79],
    [13.25, 80.06, 0.74],

    [13.08, 80.27, 0.68],
    [13.05, 80.21, 0.63],
    [13.12, 80.33, 0.58],

    [12.0, 80.02, 0.87],
    [11.95, 79.96, 0.82],

    [12.92, 79.76, 0.69],
    [13.01, 79.82, 0.64],

    [13.45, 79.15, 0.36],
    [13.4, 79.09, 0.30],
  ],

  60: [
    ...BASE_LOW,
    ...BASE_MOD,

    [12.7, 80.12, 1.0],
    [12.65, 80.06, 0.95],
    [12.76, 80.18, 0.90],

    [13.15, 80.22, 0.89],
    [13.1, 80.16, 0.84],
    [13.21, 80.28, 0.79],

    [13.08, 80.27, 0.87],
    [13.05, 80.21, 0.81],
    [13.13, 80.33, 0.77],

    [12.1, 80.12, 0.83],
    [12.05, 80.06, 0.78],

    [13.5, 79.22, 0.38],
    [13.45, 79.16, 0.33],
  ],

  120: [
    ...BASE_LOW,
    ...BASE_MOD,

    [12.85, 80.22, 0.88],
    [12.8, 80.16, 0.84],

    [13.2, 80.32, 0.86],
    [13.15, 80.26, 0.81],

    [13.08, 80.37, 0.84],
    [13.05, 80.31, 0.79],

    [12.2, 80.22, 0.68],
    [12.15, 80.16, 0.63],

    [13.6, 79.32, 0.36],
  ],

  180: [
    ...BASE_LOW,
    ...BASE_MOD,

    [13.0, 80.32, 0.68],
    [12.95, 80.26, 0.63],

    [13.25, 80.42, 0.70],
    [13.2, 80.36, 0.64],

    [13.1, 80.42, 0.66],
    [13.05, 80.36, 0.59],

    [12.3, 80.32, 0.48],

    [13.7, 79.42, 0.28],
  ],
};

/* -------------------------------------------------------------------------- */
/* Colors                                                                     */
/* -------------------------------------------------------------------------- */

const INTENSITY_COLOR: Record<
  StormCell["intensity"],
  string
> = {
  low: "#18734F",
  moderate: "#A66A00",
  severe: "#B42318",
  extreme: "#991B1B",
};

export { INTENSITY_COLOR };

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

export default function StormMap({
  activeLayer,
  timeOffset,
  onCellClick,
  selectedCell,
  isDark,
  heatmap,
  stormCells,
}: Props) {
  const mapRef = useRef<L.Map | null>(null);

  const containerRef =
    useRef<HTMLDivElement>(null);

  const heatLayerRef =
    useRef<L.HeatLayer | null>(null);

  const markersRef =
    useRef<L.LayerGroup | null>(null);

  const tileLayerRef =
    useRef<L.TileLayer | null>(null);

  const isDarkRef =
    useRef(isDark);

  isDarkRef.current = isDark;

  /* ------------------------------------------------------------------------ */
  /* Heatmap                                                                  */
  /* ------------------------------------------------------------------------ */

  const renderHeatmap = useCallback(
    (
      map: L.Map,
      offset: number,
      layer: string,
      liveHeatmap: Heatmap | null,
    ) => {
      if (heatLayerRef.current) {
        map.removeLayer(
          heatLayerRef.current
        );

        heatLayerRef.current = null;
      }

      if (
        layer !== "storm" &&
        layer !== "lightning" &&
        layer !== "radar"
      ) {
        return;
      }

      const key = Object.keys(
        HEATMAP_ZONES
      )
        .map(Number)
        .reduce((previous, current) =>
          Math.abs(current - offset) <
          Math.abs(previous - offset)
            ? current
            : previous
        );

      const data = liveHeatmap
        ? heatmapPoints(liveHeatmap)
        : HEATMAP_ZONES[key];

      let gradient: Record<
        string,
        string
      >;

      /* -------------------------------------------------------------------- */
      /* Lightning layer                                                      */
      /* -------------------------------------------------------------------- */

      if (layer === "lightning") {
        gradient = {
          0.0: "#EEF4EF",
          0.20: "#B8D2BF",
          0.40: "#D9C56A",
          0.60: "#D98A45",
          0.80: "#C65B43",
          1.0: "#B42318",
        };
      }

      /* -------------------------------------------------------------------- */
      /* Radar layer                                                          */
      /* -------------------------------------------------------------------- */

      else if (layer === "radar") {
        gradient = {
          0.0: "#EEF4EF",
          0.18: "#A9CCB3",
          0.35: "#C7D88D",
          0.50: "#DCC260",
          0.64: "#D98A45",
          0.80: "#C65B43",
          1.0: "#B42318",
        };
      }

      /* -------------------------------------------------------------------- */
      /* Storm probability layer                                             */
      /* -------------------------------------------------------------------- */

      else {
        gradient = {
          /*
           * Stronger green presence.
           * Still muted enough for a government interface.
           */
          0.0: "#E6F0E8",
          0.12: "#C4DDCB",
          0.24: "#92BE9F",
          0.36: "#6FA681",
          0.46: "#D2C36A",
          0.58: "#D89548",
          0.72: "#D0644B",
          0.90: "#B42318",
          1.0: "#8F201A",
        };
      }

      const isModelHeatmap = Boolean(liveHeatmap?.features.length);
      const heat = (
        L as any
      ).heatLayer(data, {
        radius: isModelHeatmap ? 32 : 44,
        blur: isModelHeatmap ? 24 : 30,

        maxZoom: 10,

        max: 1,

        gradient,

        /*
         * Taper off to zero opacity at edges to prevent harsh square boundaries
         */
        minOpacity: 0.0,
      });

      heat.addTo(map);

      /*
       * Automatic camera snapping to model domain bounds disabled
       * to maintain smooth user pan/zoom position across updates.
       */

      heatLayerRef.current =
        heat;
    },
    []
  );

  /* ------------------------------------------------------------------------ */
  /* Storm markers                                                            */
  /* ------------------------------------------------------------------------ */

  const renderMarkers = useCallback(
    (
      map: L.Map,
      selectedId: string | null,
      onCellClickFn: (
        cell: StormCell
      ) => void,
      cells: StormCell[],
    ) => {
      if (markersRef.current) {
        map.removeLayer(
          markersRef.current
        );
      }

      const group =
        L.layerGroup();

      cells.forEach(
        (cell) => {
          const color =
            INTENSITY_COLOR[
              cell.intensity
            ];

          const isSelected =
            cell.id === selectedId;

          /*
           * Simple, official-looking
           * storm marker.
           *
           * No neon.
           * No glow.
           * No animation.
           * No unnecessary arrows.
           */

          const icon =
            L.divIcon({
              className:
                "storm-cell-marker",
              html: `
                <div
                  style="
                    width: 18px;
                    height: 18px;
                    border-radius: 50%;
                    background: ${color}33;
                    border: 2px solid ${color};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-sizing: border-box;
                    box-shadow: ${
                      isSelected
                        ? "0 0 0 4px " + color + "33"
                        : "0 1px 3px rgba(0,0,0,0.14)"
                    };
                  "
                >
                  <span
                    style="
                      width: 5px;
                      height: 5px;
                      border-radius: 50%;
                      background: ${color};
                      display: block;
                    "
                  ></span>
                </div>
              `,
              iconSize: [
                18,
                18,
              ],
              iconAnchor: [
                9,
                9,
              ],
            });

          /* ---------------------------------------------------------------- */
          /* Popup                                                            */
          /* ---------------------------------------------------------------- */

          const popupHtml = `
            <div
              style="
                min-width:220px;
                color:var(--popup-text);
                background:var(--popup-bg);
                font-family:Inter,Arial,sans-serif;
              "
            >

              <div
                style="
                  display:flex;
                  align-items:center;
                  justify-content:space-between;
                  gap:12px;
                  padding-bottom:10px;
                  margin-bottom:10px;
                  border-bottom:1px solid var(--border-dim);
                "
              >

                <strong
                  style="
                    font-size:15px;
                    color:var(--popup-text);
                  "
                >
                  Storm Cell ${cell.id}
                </strong>

                <span
                  style="
                    font-size:10px;
                    font-weight:700;
                    text-transform:uppercase;
                    color:${color};
                  "
                >
                  ${cell.intensity}
                </span>

              </div>

              <div
                style="
                  display:grid;
                  grid-template-columns:1fr auto;
                  gap:7px 16px;
                  font-size:12px;
                "
              >

                <span
                  style="
                    color:var(--popup-label);
                  "
                >
                  Storm probability
                </span>

                <strong>
                  ${cell.probability}%
                </strong>


                <span
                  style="
                    color:var(--popup-label);
                  "
                >
                  Lightning probability
                </span>

                <strong>
                  ${cell.lightningProb}%
                </strong>


                <span
                  style="
                    color:var(--popup-label);
                  "
                >
                  Movement
                </span>

                <strong>
                  ${cell.direction} ·
                  ${cell.speed} km/h
                </strong>


                <span
                  style="
                    color:var(--popup-label);
                  "
                >
                  Estimated arrival
                </span>

                <strong
                  style="
                    color:${color};
                  "
                >
                  ${cell.eta} min
                </strong>

              </div>

              <button
                onclick="window._onCellClick('${cell.id}')"
                style="
                  margin-top:14px;
                  width:100%;
                  min-height:40px;
                  background:var(--accent-dim);
                  border:1px solid var(--accent-border);
                  border-radius:6px;
                  color:var(--accent);
                  font-size:12px;
                  font-weight:600;
                  cursor:pointer;
                "
              >
                View storm details
              </button>

            </div>
          `;

          const marker =
            L.marker(
              [
                cell.lat,
                cell.lng,
              ],
              {
                icon,
              }
            );

          marker.bindPopup(
            popupHtml,
            {
              className:
                "storm-popup",
              maxWidth: 280,
              closeButton: true,
            }
          );

          marker.on(
            "click",
            () =>
              onCellClickFn(cell)
          );

          group.addLayer(
            marker
          );
        }
      );

      group.addTo(map);

      markersRef.current =
        group;
    },
    []
  );

  /* ------------------------------------------------------------------------ */
  /* Initial map setup                                                        */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    if (
      !containerRef.current ||
      mapRef.current
    ) {
      return;
    }

    const map = L.map(
      containerRef.current,
      {
        center: [
          12.7,
          79.85,
        ],

        zoom: 9,

        zoomControl: true,

        /*
         * Keep attribution because
         * OpenStreetMap requires it.
         */
        attributionControl: true,
      }
    );

    /* ---------------------------------------------------------------------- */
    /* OpenStreetMap                                                          */
    /* ---------------------------------------------------------------------- */

    /*
     * CARTO has intentionally been removed.
     *
     * This prevents the:
     *
     * "API KEY REQUIRED"
     *
     * watermark.
     */

    const tile =
      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',

          maxZoom: 19,
        }
      );

    tile.addTo(map);

    tileLayerRef.current =
      tile;

    /* ---------------------------------------------------------------------- */
    /* Popup callback                                                         */
    /* ---------------------------------------------------------------------- */

    (
      window as any
    )._onCellClick = (
      id: string
    ) => {
      const cell =
        stormCells.find(
          (c) => c.id === id
        );

      if (cell) {
        onCellClick(cell);
      }
    };

    mapRef.current =
      map;

    /*
     * IMPORTANT:
     *
     * Custom district labels have
     * deliberately been removed.
     *
     * The map itself already provides
     * geographic labels, so we don't
     * need to place extra labels over it.
     *
     * This also prevents unnecessary
     * white label boxes from our own
     * markers.
     */

    renderHeatmap(
      map,
      0,
      "storm",
      heatmap,
    );

    renderMarkers(
      map,
      null,
      onCellClick,
      stormCells,
    );

    return () => {
      delete (
        window as any
      )._onCellClick;

      map.remove();

      mapRef.current =
        null;

      tileLayerRef.current =
        null;

      heatLayerRef.current =
        null;

      markersRef.current =
        null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ------------------------------------------------------------------------ */
  /* Theme changes                                                            */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    /*
     * The map provider does not change
     * when switching between light and
     * dark application themes.
     *
     * This keeps the map stable and
     * prevents CARTO/API-key issues.
     */

    if (!mapRef.current) {
      return;
    }

    renderMarkers(
      mapRef.current,
      selectedCell,
      onCellClick,
      stormCells,
    );

    if (
      selectedCell &&
      typeof selectedCell.lat === "number" &&
      typeof selectedCell.lng === "number" &&
      !isNaN(selectedCell.lat) &&
      !isNaN(selectedCell.lng)
    ) {
      mapRef.current.flyTo([selectedCell.lat, selectedCell.lng], 13, {
        duration: 1.2,
      });
    }
  }, [
    isDark,
    selectedCell,
    onCellClick,
    renderMarkers,
    stormCells,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Heatmap updates                                                          */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    renderHeatmap(
      mapRef.current,
      timeOffset,
      activeLayer,
      heatmap,
    );
  }, [
    activeLayer,
    timeOffset,
    renderHeatmap,
    heatmap,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Marker updates                                                           */
  /* ------------------------------------------------------------------------ */

  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    renderMarkers(
      mapRef.current,
      selectedCell,
      onCellClick,
      stormCells,
    );
  }, [
    selectedCell,
    timeOffset,
    onCellClick,
    renderMarkers,
    stormCells,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Map container                                                            */
  /* ------------------------------------------------------------------------ */

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
      }}
    />
  );
}
