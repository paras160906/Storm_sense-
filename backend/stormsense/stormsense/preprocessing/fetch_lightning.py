"""
StormSense — lightning acquisition + gridding from the OpenWeather
Historical Lightning API.

WHY THIS EXISTS
----------------
The API only takes point queries: lat/lon + radius <= 50 km, and a time
window <= 7 days 23:59:59. Your DWR Cherrapunji domain (radar at
25.268N, 91.7332E, range out to ~240 km) is way bigger than one 50 km
circle, so full coverage means tiling the domain with many query points
and merging the results. The 18-19 Aug window is only 2 days, so each
tile needs exactly ONE call (well under the 7-day cap) — the tiling is
the only complexity, not the date range.

Two stages, both usable standalone or via main():

  1. fetch_domain()   Hex-tiles a disk of radius `domain_radius_km`
                       around (center_lat, center_lon), queries the API
                       once per tile, dedupes strikes by `id` across
                       overlapping tiles, and caches raw responses to
                       disk so a re-run doesn't re-spend API calls.

  2. grid_lightning() Bins the deduped strike list into a
                       [n_timesteps, H, W] array on a regular lat/lon
                       grid at a fixed cadence (default 15 min), i.e.
                       exactly the shape StormSenseDataset expects for
                       the `lightning` input channel and for building
                       `label_lightning` (threshold count > 0 -> binary).

USAGE
-----
    python fetch_and_grid_lightning.py \
        --api-key YOUR_KEY \
        --center-lat 25.268 --center-lon 91.7332 \
        --domain-radius-km 240 --tile-radius-km 45 \
        --start 2026-08-18T00:00:00Z --end 2026-08-19T23:59:59Z \
        --grid-res-km 4 --cadence-min 15 \
        --out-dir ./lightning_cache

This writes:
    lightning_cache/raw_tiles/tile_<i>.json   (one per tile, cached)
    lightning_cache/strikes_merged.json       (deduped strike list)
    lightning_cache/lightning_grid.npz        (counts [T,H,W] + lat/lon/time axes)

NOTE ON THE DATA SOURCE ITSELF
-------------------------------
The docs describe this as derived from a global sensor network via the
ERA5 pipeline. Treat `quality`/`error` as real fields to filter on
(this script defaults to keeping "good" and "medium", dropping "bad")
rather than assuming every returned strike is equally trustworthy —
worth spot-checking a handful of returned strikes against a known storm
day before trusting it as ground truth for your labels.
"""
import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import numpy as np
import requests

API_URL = "https://demo.openweathermap.org/lightning/1.0/data"
EARTH_R_KM = 6371.0


# --------------------------------------------------------------------------- #
# Stage 1: domain tiling + fetch
# --------------------------------------------------------------------------- #
def km_to_deg_lat(km: float) -> float:
    return km / (EARTH_R_KM * math.pi / 180.0)


def km_to_deg_lon(km: float, at_lat_deg: float) -> float:
    return km / (EARTH_R_KM * math.pi / 180.0 * math.cos(math.radians(at_lat_deg)))


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def hex_tile_centers(center_lat: float, center_lon: float,
                      domain_radius_km: float, tile_radius_km: float) -> List[tuple]:
    """Hex-pack tile centers (spacing = tile_radius * sqrt(3), the
    standard circle-covering hex lattice) covering a disk of
    domain_radius_km, keeping only centers whose circle plausibly
    overlaps the domain (center within domain_radius + tile_radius)."""
    spacing_km = tile_radius_km * math.sqrt(3)
    row_spacing_km = spacing_km * math.sqrt(3) / 2  # vertical spacing between hex rows

    max_rows = int(math.ceil((domain_radius_km + tile_radius_km) / row_spacing_km)) + 1
    centers = []
    for row in range(-max_rows, max_rows + 1):
        y_km = row * row_spacing_km
        x_offset_km = (spacing_km / 2) if (row % 2 != 0) else 0.0
        max_cols = int(math.ceil((domain_radius_km + tile_radius_km) / spacing_km)) + 1
        for col in range(-max_cols, max_cols + 1):
            x_km = col * spacing_km + x_offset_km
            dist_km = math.hypot(x_km, y_km)
            if dist_km > domain_radius_km + tile_radius_km * 0.999:
                continue
            dlat = km_to_deg_lat(y_km)
            dlon = km_to_deg_lon(x_km, center_lat + dlat)
            centers.append((center_lat + dlat, center_lon + dlon))
    return centers


def fetch_tile(api_key: str, lat: float, lon: float, radius_km: float,
                start_iso: str, end_iso: str, max_retries: int = 5) -> Optional[dict]:
    params = {
        "lat": lat, "lon": lon, "radius": radius_km,
        "start_date": start_iso, "end_date": end_iso, "apikey": api_key,
    }
    backoff = 2.0
    for attempt in range(max_retries):
        resp = requests.get(API_URL, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            time.sleep(backoff)
            backoff *= 2
            continue
        print(f"  tile ({lat:.3f},{lon:.3f}) failed: {resp.status_code} {resp.text[:200]}")
        return None
    print(f"  tile ({lat:.3f},{lon:.3f}) gave up after {max_retries} retries (rate limited)")
    return None


def fetch_domain(api_key: str, center_lat: float, center_lon: float,
                  domain_radius_km: float, tile_radius_km: float,
                  start_iso: str, end_iso: str, out_dir: str,
                  sleep_between_calls: float = 0.2) -> List[dict]:
    """Returns the deduped, merged list of strike records for the whole domain."""
    assert tile_radius_km <= 50, "API caps radius at 50 km"
    raw_dir = os.path.join(out_dir, "raw_tiles")
    os.makedirs(raw_dir, exist_ok=True)

    centers = hex_tile_centers(center_lat, center_lon, domain_radius_km, tile_radius_km)
    print(f"Domain radius {domain_radius_km} km, tile radius {tile_radius_km} km "
          f"-> {len(centers)} tiles")

    all_strikes = {}
    for i, (lat, lon) in enumerate(centers):
        cache_path = os.path.join(raw_dir, f"tile_{i:04d}.json")
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                data = json.load(f)
        else:
            data = fetch_tile(api_key, lat, lon, tile_radius_km, start_iso, end_iso)
            if data is not None:
                with open(cache_path, "w") as f:
                    json.dump(data, f)
            time.sleep(sleep_between_calls)

        if not data:
            continue
        for strike in data.get("lightnings", []):
            all_strikes[strike["id"]] = strike  # dict dedupe by id

        if (i + 1) % 10 == 0 or i == len(centers) - 1:
            print(f"  tile {i + 1}/{len(centers)}: {len(all_strikes)} unique strikes so far")

    merged = list(all_strikes.values())
    with open(os.path.join(out_dir, "strikes_merged.json"), "w") as f:
        json.dump(merged, f)
    print(f"Merged: {len(merged)} unique strikes across domain")
    return merged


# --------------------------------------------------------------------------- #
# Stage 2: gridding onto the model's [T, H, W] format
# --------------------------------------------------------------------------- #
@dataclass
class GridSpec:
    center_lat: float
    center_lon: float
    domain_radius_km: float
    res_km: float

    def build_axes(self):
        n = int(2 * self.domain_radius_km / self.res_km) + 1
        offsets_km = (np.arange(n) - n // 2) * self.res_km
        lats = self.center_lat + np.array([km_to_deg_lat(k) for k in offsets_km])
        lons = self.center_lon + np.array(
            [km_to_deg_lon(k, self.center_lat) for k in offsets_km]
        )
        return lats, lons  # both length n; grid is lats[i] x lons[j]


def grid_lightning(strikes: List[dict], grid: GridSpec,
                    start_dt: datetime, end_dt: datetime,
                    cadence_min: int = 15,
                    min_quality: str = "medium") -> dict:
    """
    Bins strikes into [n_timesteps, H, W] strike-count grids.

    min_quality: keep strikes with quality in {"good"} if min_quality=="good",
                 or {"good","medium"} if min_quality=="medium" (drops "bad"/"undefined").
    Returns dict with keys: counts [T,H,W] int32, lats [H], lons [W],
    time_edges [T+1] (UTC datetimes as ISO strings), dropped_count.
    """
    quality_rank = {"bad": 0, "undefined": 0, "medium": 1, "good": 2}
    min_rank = quality_rank.get(min_quality, 1)

    lats, lons = grid.build_axes()
    H, W = len(lats), len(lons)
    lat_edges = np.concatenate([[lats[0] - (lats[1] - lats[0]) / 2],
                                 (lats[:-1] + lats[1:]) / 2,
                                 [lats[-1] + (lats[-1] - lats[-2]) / 2]])
    lon_edges = np.concatenate([[lons[0] - (lons[1] - lons[0]) / 2],
                                 (lons[:-1] + lons[1:]) / 2,
                                 [lons[-1] + (lons[-1] - lons[-2]) / 2]])

    total_seconds = (end_dt - start_dt).total_seconds()
    n_steps = int(math.ceil(total_seconds / (cadence_min * 60)))
    time_edges = [start_dt + timedelta(minutes=cadence_min * k) for k in range(n_steps + 1)]

    counts = np.zeros((n_steps, H, W), dtype=np.int32)
    dropped = 0

    for s in strikes:
        if quality_rank.get(s.get("quality", "undefined"), 0) < min_rank:
            dropped += 1
            continue
        dt = datetime.fromisoformat(s["datetime"].replace("Z", "+00:00"))
        if not (start_dt <= dt < end_dt):
            continue
        t_idx = int((dt - start_dt).total_seconds() // (cadence_min * 60))
        if not (0 <= t_idx < n_steps):
            continue
        row = np.searchsorted(lat_edges, s["lat"]) - 1
        col = np.searchsorted(lon_edges, s["lon"]) - 1
        if 0 <= row < H and 0 <= col < W:
            counts[t_idx, row, col] += 1

    print(f"Gridded {counts.sum()} strikes into [{n_steps}, {H}, {W}] "
          f"({dropped} dropped for quality)")
    return {
        "counts": counts,
        "lats": lats,
        "lons": lons,
        "time_edges": [t.isoformat() for t in time_edges],
        "dropped_count": dropped,
    }


# --------------------------------------------------------------------------- #
# Self-test with synthetic data (no network) — run with --self-test
# --------------------------------------------------------------------------- #
def _self_test():
    print("Running self-test with synthetic strikes (no API calls)...")
    grid = GridSpec(center_lat=25.268, center_lon=91.7332, domain_radius_km=240, res_km=4)
    lats, lons = grid.build_axes()
    print(f"Grid axes: {len(lats)} x {len(lons)} at ~{grid.res_km}km res "
          f"(lat {lats.min():.2f}..{lats.max():.2f}, lon {lons.min():.2f}..{lons.max():.2f})")

    start_dt = datetime(2026, 8, 18, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 8, 18, 1, 0, tzinfo=timezone.utc)  # 4 x 15-min steps

    # 3 strikes: two in the same 15-min/grid cell (should sum to 2), one
    # in a later timestep, one with quality "bad" (should be dropped),
    # one clearly outside the time window (should be excluded).
    synthetic = [
        {"id": "a", "datetime": "2026-08-18T00:03:00+00:00", "lat": 25.268, "lon": 91.7332, "quality": "good", "error": 3.0},
        {"id": "b", "datetime": "2026-08-18T00:07:00+00:00", "lat": 25.269, "lon": 91.7340, "quality": "medium", "error": 5.0},
        {"id": "c", "datetime": "2026-08-18T00:40:00+00:00", "lat": 25.30, "lon": 91.80, "quality": "good", "error": 2.0},
        {"id": "d", "datetime": "2026-08-18T00:10:00+00:00", "lat": 25.268, "lon": 91.7332, "quality": "bad", "error": 20.0},
        {"id": "e", "datetime": "2026-08-18T02:00:00+00:00", "lat": 25.268, "lon": 91.7332, "quality": "good", "error": 2.0},
    ]

    result = grid_lightning(synthetic, grid, start_dt, end_dt, cadence_min=15, min_quality="medium")
    counts = result["counts"]
    assert counts.shape[0] == 4, f"expected 4 timesteps, got {counts.shape[0]}"
    assert result["dropped_count"] == 1, f"expected 1 dropped (quality), got {result['dropped_count']}"
    assert counts[0].sum() == 2, f"expected 2 strikes in timestep 0 (a+b), got {counts[0].sum()}"
    assert counts[2].sum() == 1, f"expected 1 strike in timestep 2 (c), got {counts[2].sum()}"
    assert counts.sum() == 3, f"strike 'e' outside window and 'd' bad-quality should be excluded, got total {counts.sum()}"

    # tiling sanity: hex centers should cover the domain edge without
    # gaps bigger than the tile radius
    centers = hex_tile_centers(25.268, 91.7332, domain_radius_km=240, tile_radius_km=45)
    max_dist = max(haversine_km(25.268, 91.7332, la, lo) for la, lo in centers)
    assert max_dist >= 240, f"tiling doesn't reach domain edge: max center dist {max_dist:.0f}km"
    print(f"Tiling: {len(centers)} tiles, furthest center {max_dist:.0f}km from radar "
          f"(covers to {max_dist + 45:.0f}km with 45km tile radius)")

    print("All self-test assertions passed.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true", help="run offline synthetic test and exit")
    ap.add_argument("--api-key", default=os.environ.get("OWM_API_KEY"))
    ap.add_argument("--center-lat", type=float, default=25.268)
    ap.add_argument("--center-lon", type=float, default=91.7332)
    ap.add_argument("--domain-radius-km", type=float, default=240.0)
    ap.add_argument("--tile-radius-km", type=float, default=45.0)
    ap.add_argument("--start", required=False, help="ISO-8601 UTC, e.g. 2026-08-18T00:00:00Z")
    ap.add_argument("--end", required=False, help="ISO-8601 UTC, e.g. 2026-08-19T23:59:59Z")
    ap.add_argument("--grid-res-km", type=float, default=4.0)
    ap.add_argument("--cadence-min", type=int, default=15)
    ap.add_argument("--min-quality", choices=["good", "medium"], default="medium")
    ap.add_argument("--out-dir", default="./lightning_cache")
    args = ap.parse_args()

    if args.self_test:
        _self_test()
        return

    if not args.api_key:
        raise SystemExit("Need --api-key (or set OWM_API_KEY env var)")
    if not args.start or not args.end:
        raise SystemExit("Need --start and --end (ISO-8601 UTC)")

    os.makedirs(args.out_dir, exist_ok=True)
    strikes = fetch_domain(
        args.api_key, args.center_lat, args.center_lon,
        args.domain_radius_km, args.tile_radius_km,
        args.start, args.end, args.out_dir,
    )

    grid = GridSpec(args.center_lat, args.center_lon, args.domain_radius_km, args.grid_res_km)
    start_dt = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    result = grid_lightning(strikes, grid, start_dt, end_dt,
                             cadence_min=args.cadence_min, min_quality=args.min_quality)

    out_path = os.path.join(args.out_dir, "lightning_grid.npz")
    np.savez_compressed(
        out_path,
        counts=result["counts"],
        lats=result["lats"],
        lons=result["lons"],
        time_edges=np.array(result["time_edges"]),
    )
    print(f"Wrote {out_path}: counts shape {result['counts'].shape}")


if __name__ == "__main__":
    main()
