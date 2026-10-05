"""
StormSense — regridding + dataset assembly pipeline.

Takes the four raw sources you downloaded (INSAT-3DR L1B .h5, DWR
Cherrapunji volume-scan .nc, ERA5 CAPE/CIN .nc, + the lightning_grid.npz
from fetch_and_grid_lightning.py) and produces the per-timestep .npz
files StormSenseDataset (in stormsense_model.py) expects:

    insat[7,H,W]  radar[2,H,W]  era5[2,H,W]  lightning[1,H,W]
    label_lightning[n_lead,H,W]  label_intensity[n_lead,H,W]

all on ONE common grid: the exact same GridSpec (center 25.268N/91.7332E,
domain_radius_km=240, res_km=4 -> 121x121) used by
fetch_and_grid_lightning.py, so every modality lines up pixel-for-pixel
with zero further alignment work downstream.

WHY EACH SOURCE NEEDS DIFFERENT TREATMENT
------------------------------------------
INSAT-3DR L1B: full-disk swath, raw 10-bit digital counts, each channel
    at its own resolution with its own per-pixel Latitude/Longitude
    arrays (not a regular grid) and its own count->physical-unit LUT.
    -> crop to domain bbox, apply LUT, scatter-interpolate onto target grid.

DWR Cherrapunji: polar volume scan (10 sweeps x 360 rays x 1600 range
    gates), not gridded at all. -> convert every gate to (lat, lon,
    height-ASL) with the 4/3-earth-radius beam model, keep gates near
    the CAPPI altitude, scatter-interpolate onto target grid.

ERA5 CAPE/CIN: already a regular lat/lon grid, hourly. -> just
    bilinear-interpolate in space and linear-interpolate in time.
    Cheapest of the three, no scatter step needed.

Two phases, run separately so a partial/interrupted run never loses work:

  Phase 1 (`frames`):  raw files -> one cached "frame" npz per available
                        15-min slot, containing insat/radar/era5/lightning
                        only (no labels yet, since labels need FUTURE
                        frames that may not exist yet on a partial run).

  Phase 2 (`dataset`):  walks the sorted frame cache and, for every frame
                        that has enough future frames to cover
                        max(lead_times), stamps on label_lightning /
                        label_intensity (from the *future* frames'
                        lightning/radar) and writes the final npz into
                        --dataset-dir. This final directory is exactly
                        what you point StormSenseDataset(data_dir=...) at.

USAGE
-----
    # Phase 1: build frames from a batch of downloaded files
    python build_dataset.py frames \
        --insat-dir  D:/SIH2026/INSAT3DR/3RIMG_L1B_STD/2026/18AUG \
        --dwr-dir    D:/SIH2026/DWR/RSCHR_L2B_STD/2026/18AUG \
        --era5-file  63feed296d7301efdf43dcf0b6f9a460.nc \
        --lightning-grid lightning_cache/lightning_grid.npz \
        --start 2026-08-18T00:00:00Z --end 2026-08-20T00:00:00Z \
        --frames-dir ./frames

    # Phase 2: turn frames into the final labeled training set
    python build_dataset.py dataset --frames-dir ./frames --dataset-dir ./dataset

    # Sanity-check the regridders against one file each, no directory scan
    python build_dataset.py selftest --insat-file 3RIMG_..._L1B_STD_V01R00.h5 \
        --dwr-file RSCHR_..._L2B_STD.nc --era5-file 63feed....nc
"""
import argparse
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import h5py
import numpy as np
from scipy.interpolate import griddata, RegularGridInterpolator

try:
    import xarray as xr
except ImportError:
    xr = None

EARTH_R_KM = 6371.0
EARTH_R_M = 6371000.0

LEAD_TIMES = (1, 2, 4, 8, 12)          # in 15-min steps -> 15,30,60,120,180 min
CADENCE_MIN = 15
INTENSITY_DBZ_THRESHOLD = 35.0          # DBZ >= this in a future radar frame -> "intensity" positive


# --------------------------------------------------------------------------- #
# Common grid (must match fetch_and_grid_lightning.py's GridSpec exactly)
# --------------------------------------------------------------------------- #
def km_to_deg_lat(km: float) -> float:
    return km / (EARTH_R_KM * math.pi / 180.0)


def km_to_deg_lon(km: float, at_lat_deg: float) -> float:
    return km / (EARTH_R_KM * math.pi / 180.0 * math.cos(math.radians(at_lat_deg)))


@dataclass
class GridSpec:
    center_lat: float = 25.268
    center_lon: float = 91.7332
    domain_radius_km: float = 240.0
    res_km: float = 4.0

    def build_axes(self):
        n = int(2 * self.domain_radius_km / self.res_km) + 1
        offsets_km = (np.arange(n) - n // 2) * self.res_km
        lats = self.center_lat + np.array([km_to_deg_lat(k) for k in offsets_km])
        lons = self.center_lon + np.array(
            [km_to_deg_lon(k, self.center_lat) for k in offsets_km]
        )
        return lats, lons

    def meshgrid(self):
        lats, lons = self.build_axes()
        lon_mesh, lat_mesh = np.meshgrid(lons, lats)  # both [H,W], row=lat, col=lon
        return lat_mesh, lon_mesh

    def bbox_with_margin(self, margin_km: float = 20.0):
        dlat = km_to_deg_lat(self.domain_radius_km + margin_km)
        dlon = km_to_deg_lon(self.domain_radius_km + margin_km, self.center_lat)
        return (self.center_lat - dlat, self.center_lat + dlat,
                self.center_lon - dlon, self.center_lon + dlon)


def scatter_regrid(src_lat: np.ndarray, src_lon: np.ndarray, src_val: np.ndarray,
                    lat_mesh: np.ndarray, lon_mesh: np.ndarray,
                    method: str = "linear") -> np.ndarray:
    """Regrid scattered (lat,lon,val) onto target (lat_mesh,lon_mesh) via
    griddata, with a nearest-neighbor fallback to fill any NaNs `linear`
    leaves outside the convex hull of the source points."""
    pts = np.column_stack([src_lat.ravel(), src_lon.ravel()])
    vals = src_val.ravel()
    finite = np.isfinite(vals) & np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    pts, vals = pts[finite], vals[finite]
    if len(vals) == 0:
        return np.full(lat_mesh.shape, np.nan, dtype=np.float32)
    target = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
    out = griddata(pts, vals, target, method=method)
    nan_mask = np.isnan(out)
    if nan_mask.any():
        out_nn = griddata(pts, vals, target[nan_mask], method="nearest")
        out[nan_mask] = out_nn
    return out.reshape(lat_mesh.shape).astype(np.float32)


# --------------------------------------------------------------------------- #
# INSAT-3DR L1B loader
# --------------------------------------------------------------------------- #
INSAT_FNAME_RE = re.compile(r"3RIMG_(\d{2}[A-Z]{3}\d{4})_(\d{4})_L1B")


def parse_insat_timestamp(path: str) -> Optional[datetime]:
    m = INSAT_FNAME_RE.search(os.path.basename(path))
    if not m:
        return None
    dt = datetime.strptime(m.group(1) + m.group(2), "%d%b%Y%H%M")
    return dt.replace(tzinfo=timezone.utc)


def _crop_by_bbox(lat, lon, bbox):
    lat_min, lat_max, lon_min, lon_max = bbox
    rows = np.where((lat.min(axis=1) <= lat_max) & (lat.max(axis=1) >= lat_min))[0]
    cols = np.where((lon.min(axis=0) <= lon_max) & (lon.max(axis=0) >= lon_min))[0]
    if len(rows) == 0 or len(cols) == 0:
        return slice(0, 0), slice(0, 0)
    return slice(rows.min(), rows.max() + 1), slice(cols.min(), cols.max() + 1)


def load_insat_frame(h5_path: str, grid: GridSpec) -> np.ndarray:
    """Returns [7, H, W] float32: TIR1_K, TIR2_K, MIR_K, WV_K, VIS_alb, BT_diff, is_day."""
    lat_mesh, lon_mesh = grid.meshgrid()
    bbox = grid.bbox_with_margin(margin_km=20.0)

    with h5py.File(h5_path, "r") as f:
        def lut_channel(name):
            lat = f["Latitude"][:].astype(np.float64) * f["Latitude"].attrs["scale_factor"][0]
            lon = f["Longitude"][:].astype(np.float64) * f["Longitude"].attrs["scale_factor"][0]
            fill = f["Latitude"].attrs["_FillValue"][0]
            counts = f[name][0].astype(np.int32)
            lut = f[f"{name}_TEMP"][:]
            lut_fill = f[f"{name}_TEMP"].attrs["_FillValue"][0]
            r0, r1 = _crop_by_bbox(np.where(lat == fill, np.nan, lat),
                                    np.where(lon == fill, np.nan, lon), bbox)
            lat_c, lon_c, counts_c = lat[r0, r1], lon[r0, r1], counts[r0, r1]
            phys = lut[np.clip(counts_c, 0, 1023)]
            phys = np.where(phys == lut_fill, np.nan, phys)
            lat_c = np.where(lat_c == fill, np.nan, lat_c)
            lon_c = np.where(lon_c == fill, np.nan, lon_c)
            return scatter_regrid(lat_c, lon_c, phys, lat_mesh, lon_mesh, method="linear")

        tir1 = lut_channel("IMG_TIR1")
        tir2 = lut_channel("IMG_TIR2")
        mir = lut_channel("IMG_MIR")
        wv = lut_channel("IMG_WV")

        # VIS is on its own (finer) grid with its own scale factor
        lat_v = f["Latitude_VIS"][:].astype(np.float64) * f["Latitude_VIS"].attrs["scale_factor"][0]
        lon_v = f["Longitude_VIS"][:].astype(np.float64) * f["Longitude_VIS"].attrs["scale_factor"][0]
        fill_v = f["Latitude_VIS"].attrs["_FillValue"][0]
        r0, r1 = _crop_by_bbox(np.where(lat_v == fill_v, np.nan, lat_v),
                                np.where(lon_v == fill_v, np.nan, lon_v), bbox)
        vis_counts = f["IMG_VIS"][0][r0, r1].astype(np.int32)
        vis_lut = f["IMG_VIS_ALBEDO"][:]
        vis_phys = vis_lut[np.clip(vis_counts, 0, 1023)]
        lat_v_c = np.where(lat_v[r0, r1] == fill_v, np.nan, lat_v[r0, r1])
        lon_v_c = np.where(lon_v[r0, r1] == fill_v, np.nan, lon_v[r0, r1])
        vis = scatter_regrid(lat_v_c, lon_v_c, vis_phys, lat_mesh, lon_mesh, method="linear")

        # is_day from per-pixel Sun_Elevation (same grid as TIR channels)
        lat = f["Latitude"][:].astype(np.float64) * f["Latitude"].attrs["scale_factor"][0]
        lon = f["Longitude"][:].astype(np.float64) * f["Longitude"].attrs["scale_factor"][0]
        fill = f["Latitude"].attrs["_FillValue"][0]
        r0, r1 = _crop_by_bbox(np.where(lat == fill, np.nan, lat),
                                np.where(lon == fill, np.nan, lon), bbox)
        sun_el = (f["Sun_Elevation"][0][r0, r1].astype(np.float32)
                  * f["Sun_Elevation"].attrs["scale_factor"][0])
        lat_c = np.where(lat[r0, r1] == fill, np.nan, lat[r0, r1])
        lon_c = np.where(lon[r0, r1] == fill, np.nan, lon[r0, r1])
        is_day = (scatter_regrid(lat_c, lon_c, sun_el, lat_mesh, lon_mesh, method="nearest") > 0).astype(np.float32)

    bt_diff = tir1 - tir2
    return np.stack([tir1, tir2, mir, wv, vis, bt_diff, is_day], axis=0).astype(np.float32)


# --------------------------------------------------------------------------- #
# DWR Cherrapunji volume-scan -> pseudo-CAPPI loader
# --------------------------------------------------------------------------- #
DWR_FNAME_RE = re.compile(r"RSCHR_(\d{2}[A-Z]{3}\d{4})_(\d{6})_L2B")


def parse_dwr_timestamp(path: str) -> Optional[datetime]:
    m = DWR_FNAME_RE.search(os.path.basename(path))
    if not m:
        return None
    dt = datetime.strptime(m.group(1) + m.group(2), "%d%b%Y%H%M%S")
    return dt.replace(tzinfo=timezone.utc)


def _beam_height_and_ground_range(range_m, elev_deg, radar_alt_m):
    """4/3-earth-radius beam propagation model: returns (height_m_ASL, ground_range_m)."""
    Re = EARTH_R_M * 4.0 / 3.0
    el = np.radians(elev_deg)
    h = np.sqrt(range_m ** 2 + Re ** 2 + 2 * range_m * Re * np.sin(el)) - Re + radar_alt_m
    s = Re * np.arcsin(range_m * np.cos(el) / (Re + h))
    return h, s


def _destination_point(lat0_deg, lon0_deg, azimuth_deg, ground_range_m):
    """Geodesic destination point given a start point, bearing, and distance."""
    R = EARTH_R_M
    lat0, lon0, brng = map(math.radians, (lat0_deg, lon0_deg, azimuth_deg))
    d_r = ground_range_m / R
    lat1 = np.arcsin(np.sin(lat0) * np.cos(d_r) + np.cos(lat0) * np.sin(d_r) * np.cos(brng))
    lon1 = lon0 + np.arctan2(np.sin(brng) * np.sin(d_r) * np.cos(lat0),
                              np.cos(d_r) - np.sin(lat0) * np.sin(lat1))
    return np.degrees(lat1), np.degrees(lon1)


def load_dwr_cappi(nc_path: str, grid: GridSpec, cappi_alt_km: float = 2.5,
                    height_tol_km: float = 0.75) -> np.ndarray:
    """Returns [2, H, W] float32: [dBZ CAPPI, valid_mask]."""
    if xr is None:
        raise RuntimeError("xarray required for DWR loading (pip install xarray netCDF4)")
    lat_mesh, lon_mesh = grid.meshgrid()

    ds = xr.open_dataset(nc_path, decode_times=False)
    n_sweeps = ds.sizes["sweep"]
    rays_per_sweep = ds.sizes["time"] // n_sweeps
    dbz = ds["DBZ"].values.reshape(n_sweeps, rays_per_sweep, -1)      # [sweep, ray, range]
    elev = ds["elevation"].values.reshape(n_sweeps, rays_per_sweep)[:, 0]  # deg, one per sweep
    azim = ds["azimuth"].values.reshape(n_sweeps, rays_per_sweep)     # deg, per ray
    rng = ds["range"].values                                          # meters
    radar_lat, radar_lon = float(ds["latitude"]), float(ds["longitude"])
    radar_alt = float(ds["altitude"])

    target_alt_m = cappi_alt_km * 1000.0
    tol_m = height_tol_km * 1000.0

    lats_all, lons_all, vals_all = [], [], []
    for si in range(n_sweeps):
        h, s = _beam_height_and_ground_range(rng[None, :], elev[si], radar_alt)  # [1,range]
        near = np.abs(h[0] - target_alt_m) <= tol_m
        if not near.any():
            continue
        rng_idx = np.where(near)[0]
        s_sel = s[0, rng_idx]                                          # [n_range_sel]
        az_sel = azim[si]                                              # [ray]
        # broadcast rays x selected ranges
        lat_pts, lon_pts = _destination_point(radar_lat, radar_lon,
                                               az_sel[:, None], s_sel[None, :])
        val_pts = dbz[si][:, rng_idx]
        lats_all.append(lat_pts.ravel())
        lons_all.append(lon_pts.ravel())
        vals_all.append(val_pts.ravel())

    if not lats_all:
        # no sweep intersects the requested altitude within tolerance anywhere in range
        dbz_grid = np.full(lat_mesh.shape, np.nan, dtype=np.float32)
        valid = np.zeros(lat_mesh.shape, dtype=np.float32)
        return np.stack([np.nan_to_num(dbz_grid, nan=-999.0), valid], axis=0)

    lats_all = np.concatenate(lats_all)
    lons_all = np.concatenate(lons_all)
    vals_all = np.concatenate(vals_all)
    finite = np.isfinite(vals_all)
    lats_all, lons_all, vals_all = lats_all[finite], lons_all[finite], vals_all[finite]

    if len(vals_all) == 0:
        dbz_grid = np.full(lat_mesh.shape, -999.0, dtype=np.float32)
        valid = np.zeros(lat_mesh.shape, dtype=np.float32)
        return np.stack([dbz_grid, valid], axis=0)

    # coverage mask: which target cells actually have a gate within ~1 grid cell of them
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack([lats_all, lons_all]))
    target_pts = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
    max_gate_spacing_deg = km_to_deg_lat(grid.res_km * 1.5)
    dist, _ = tree.query(target_pts, k=1)
    valid = (dist <= max_gate_spacing_deg).astype(np.float32).reshape(lat_mesh.shape)

    dbz_grid = scatter_regrid(lats_all, lons_all, vals_all, lat_mesh, lon_mesh, method="nearest")
    dbz_grid = np.where(valid > 0, dbz_grid, -999.0).astype(np.float32)  # -999 sentinel where no coverage
    return np.stack([dbz_grid, valid], axis=0)


# --------------------------------------------------------------------------- #
# ERA5 CAPE/CIN loader (already gridded -> bilinear + time interpolation)
# --------------------------------------------------------------------------- #
def load_era5_frame(nc_path_or_ds, grid: GridSpec, target_time: datetime) -> np.ndarray:
    """Returns [2, H, W] float32: [CAPE, CIN], bilinear-in-space + linear-in-time."""
    if xr is None:
        raise RuntimeError("xarray required for ERA5 loading")
    ds = nc_path_or_ds if hasattr(nc_path_or_ds, "data_vars") else xr.open_dataset(nc_path_or_ds)
    lat_mesh, lon_mesh = grid.meshgrid()

    times = ds["valid_time"].values.astype("datetime64[s]").astype(datetime)
    times = [t.replace(tzinfo=timezone.utc) for t in times]
    if target_time <= times[0]:
        i0, i1, w = 0, 0, 0.0
    elif target_time >= times[-1]:
        i0, i1, w = len(times) - 1, len(times) - 1, 0.0
    else:
        i1 = next(i for i, t in enumerate(times) if t >= target_time)
        i0 = i1 - 1
        span = (times[i1] - times[i0]).total_seconds()
        w = 0.0 if span == 0 else (target_time - times[i0]).total_seconds() / span

    lat_src = ds["latitude"].values
    lon_src = ds["longitude"].values
    lat_order = np.argsort(lat_src)  # RegularGridInterpolator needs ascending axes
    lat_src_sorted = lat_src[lat_order]

    out = []
    for var in ("cape", "cin"):
        f0 = ds[var].isel(valid_time=i0).values[lat_order, :]
        f1 = ds[var].isel(valid_time=i1).values[lat_order, :]
        frame = (1 - w) * f0 + w * f1
        interp = RegularGridInterpolator((lat_src_sorted, lon_src), frame,
                                          bounds_error=False, fill_value=None)
        pts = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
        out.append(interp(pts).reshape(lat_mesh.shape).astype(np.float32))
    return np.stack(out, axis=0)


# --------------------------------------------------------------------------- #
# Lightning loader (already gridded by fetch_and_grid_lightning.py)
# --------------------------------------------------------------------------- #
class LightningGrid:
    def __init__(self, npz_path: Optional[str]):
        self.available = npz_path is not None and os.path.exists(npz_path)
        if self.available:
            d = np.load(npz_path, allow_pickle=True)
            self.counts = d["counts"]  # [T,H,W]
            self.time_edges = [datetime.fromisoformat(s) for s in d["time_edges"]]

    def slice_at(self, target_time: datetime) -> Tuple[np.ndarray, bool]:
        """Returns ([1,H,W] float32 strike counts, had_data: bool)."""
        if not self.available:
            return None, False
        for t_idx in range(len(self.time_edges) - 1):
            if self.time_edges[t_idx] <= target_time < self.time_edges[t_idx + 1]:
                return self.counts[t_idx][None].astype(np.float32), True
        return None, False


# --------------------------------------------------------------------------- #
# File discovery
# --------------------------------------------------------------------------- #
def scan_dir(dir_path: str, pattern_fn) -> List[Tuple[datetime, str]]:
    out = []
    for root, _, files in os.walk(dir_path):
        for fn in files:
            full = os.path.join(root, fn)
            ts = pattern_fn(full)
            if ts is not None:
                out.append((ts, full))
    return sorted(out)


def nearest_file(indexed: List[Tuple[datetime, str]], target: datetime,
                  tolerance_min: float) -> Optional[str]:
    if not indexed:
        return None
    best_dt, best_path, best_diff = None, None, None
    for ts, path in indexed:
        diff = abs((ts - target).total_seconds()) / 60.0
        if best_diff is None or diff < best_diff:
            best_dt, best_path, best_diff = ts, path, diff
    if best_diff is not None and best_diff <= tolerance_min:
        return best_path
    return None


# --------------------------------------------------------------------------- #
# Phase 1: build cached per-timestep frames
# --------------------------------------------------------------------------- #
def build_frames(insat_dir: str, dwr_dir: str, era5_file: str, lightning_grid_path: Optional[str],
                  start: datetime, end: datetime, frames_dir: str, grid: GridSpec,
                  insat_tol_min: float = 20.0, dwr_tol_min: float = 20.0):
    os.makedirs(frames_dir, exist_ok=True)
    insat_files = scan_dir(insat_dir, parse_insat_timestamp)
    dwr_files = scan_dir(dwr_dir, parse_dwr_timestamp)
    print(f"Found {len(insat_files)} INSAT files, {len(dwr_files)} DWR files")

    era5_ds = xr.open_dataset(era5_file)
    lightning = LightningGrid(lightning_grid_path)

    n_steps = int((end - start).total_seconds() // (CADENCE_MIN * 60))
    written, skipped = 0, 0
    for k in range(n_steps):
        t = start + timedelta(minutes=CADENCE_MIN * k)
        out_path = os.path.join(frames_dir, f"{t.strftime('%Y%m%d_%H%M')}.npz")
        if os.path.exists(out_path):
            continue

        insat_path = nearest_file(insat_files, t, insat_tol_min)
        dwr_path = nearest_file(dwr_files, t, dwr_tol_min)
        if insat_path is None and dwr_path is None:
            skipped += 1
            continue  # nothing to anchor this timestep on; leave a gap rather than write junk

        insat = (load_insat_frame(insat_path, grid) if insat_path
                 else np.zeros((7, *grid.meshgrid()[0].shape), dtype=np.float32))
        radar = (load_dwr_cappi(dwr_path, grid) if dwr_path
                 else np.zeros((2, *grid.meshgrid()[0].shape), dtype=np.float32))
        era5 = load_era5_frame(era5_ds, grid, t)
        light, had_light = lightning.slice_at(t)
        if light is None:
            light = np.zeros((1, *grid.meshgrid()[0].shape), dtype=np.float32)

        np.savez_compressed(
            out_path,
            insat=insat.astype(np.float16), radar=radar.astype(np.float16),
            era5=era5.astype(np.float16), lightning=light.astype(np.float16),
            presence_insat=np.float32(insat_path is not None),
            presence_radar=np.float32(dwr_path is not None),
            presence_lightning=np.float32(had_light),
        )
        written += 1
        print(f"  [{k+1}/{n_steps}] {t.isoformat()} -> {out_path} "
              f"(insat={'y' if insat_path else 'n'} radar={'y' if dwr_path else 'n'} "
              f"lightning={'y' if had_light else 'n'})")

    print(f"Phase 1 done: {written} frames written, {skipped} timesteps skipped (no source data)")


# --------------------------------------------------------------------------- #
# Phase 2: stamp labels from future frames -> final training-ready dataset
# --------------------------------------------------------------------------- #
def build_dataset(frames_dir: str, dataset_dir: str, lead_times=LEAD_TIMES):
    os.makedirs(dataset_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".npz"))
    stamps = [datetime.strptime(f[:-4], "%Y%m%d_%H%M").replace(tzinfo=timezone.utc) for f in files]
    by_time = dict(zip(stamps, files))
    max_lead = max(lead_times)

    written, incomplete = 0, 0
    for i, t in enumerate(stamps):
        needed = [t + timedelta(minutes=CADENCE_MIN * lt) for lt in lead_times]
        if any(nt not in by_time for nt in needed):
            incomplete += 1
            continue  # not enough future coverage yet to label this timestep

        cur = np.load(os.path.join(frames_dir, files[i]))
        label_light, label_inten = [], []
        for nt in needed:
            fut = np.load(os.path.join(frames_dir, by_time[nt]))
            fut_light = fut["lightning"][0]
            fut_radar_dbz = fut["radar"][0]
            fut_radar_valid = fut["radar"][1]
            label_light.append((fut_light > 0).astype(np.float32))
            inten = ((fut_radar_dbz >= INTENSITY_DBZ_THRESHOLD) & (fut_radar_valid > 0)).astype(np.float32)
            label_inten.append(inten)

        out_path = os.path.join(dataset_dir, files[i])
        np.savez_compressed(
            out_path,
            insat=cur["insat"], radar=cur["radar"], era5=cur["era5"], lightning=cur["lightning"],
            label_lightning=np.stack(label_light, axis=0),
            label_intensity=np.stack(label_inten, axis=0),
        )
        written += 1

    print(f"Phase 2 done: {written} labeled training frames written to {dataset_dir} "
          f"({incomplete} frames skipped — not enough future coverage for lead times {lead_times})")


# --------------------------------------------------------------------------- #
# Self-test against one real file per modality (no directory scan needed)
# --------------------------------------------------------------------------- #
def _selftest(insat_file, dwr_file, era5_file):
    grid = GridSpec()
    lat_mesh, lon_mesh = grid.meshgrid()
    print(f"Grid: {lat_mesh.shape[0]}x{lat_mesh.shape[1]}, "
          f"lat {lat_mesh.min():.3f}..{lat_mesh.max():.3f}, lon {lon_mesh.min():.3f}..{lon_mesh.max():.3f}")

    if insat_file:
        insat = load_insat_frame(insat_file, grid)
        names = ["TIR1_K", "TIR2_K", "MIR_K", "WV_K", "VIS_alb", "BT_diff", "is_day"]
        print("\nINSAT channels:")
        for name, ch in zip(names, insat):
            finite = ch[np.isfinite(ch)]
            print(f"  {name:8s} shape={ch.shape} finite={finite.size}/{ch.size} "
                  f"min={finite.min() if finite.size else float('nan'):.2f} "
                  f"max={finite.max() if finite.size else float('nan'):.2f}")

    if dwr_file:
        radar = load_dwr_cappi(dwr_file, grid, cappi_alt_km=2.5)
        dbz, valid = radar
        covered = dbz[valid > 0]
        print("\nDWR pseudo-CAPPI @2.5km:")
        print(f"  coverage: {(valid > 0).sum()}/{valid.size} cells "
              f"({100*(valid>0).mean():.1f}%)")
        if covered.size:
            print(f"  dBZ over covered cells: min={covered.min():.1f} max={covered.max():.1f} "
                  f"mean={covered.mean():.1f}")

    if era5_file:
        era5_ds = xr.open_dataset(era5_file)
        t0 = datetime.fromisoformat(str(era5_ds["valid_time"].values[0])[:19] + "+00:00")
        era5 = load_era5_frame(era5_ds, grid, t0 + timedelta(hours=1, minutes=30))
        cape, cin = era5
        print(f"\nERA5 @ {(t0 + timedelta(hours=1, minutes=30)).isoformat()} (interpolated):")
        print(f"  CAPE: min={cape.min():.1f} max={cape.max():.1f} mean={cape.mean():.1f} J/kg")
        print(f"  CIN:  min={cin.min():.1f} max={cin.max():.1f} mean={cin.mean():.1f} J/kg")

    print("\nSelf-test complete — all regridders ran without error on the sample files.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("frames", help="Phase 1: raw files -> cached per-timestep frames")
    p1.add_argument("--insat-dir", required=True)
    p1.add_argument("--dwr-dir", required=True)
    p1.add_argument("--era5-file", required=True)
    p1.add_argument("--lightning-grid", default=None)
    p1.add_argument("--start", required=True)
    p1.add_argument("--end", required=True)
    p1.add_argument("--frames-dir", default="./frames")

    p2 = sub.add_parser("dataset", help="Phase 2: frames -> labeled training set")
    p2.add_argument("--frames-dir", default="./frames")
    p2.add_argument("--dataset-dir", default="./dataset")

    p3 = sub.add_parser("selftest", help="Sanity-check regridders on one file per modality")
    p3.add_argument("--insat-file", default=None)
    p3.add_argument("--dwr-file", default=None)
    p3.add_argument("--era5-file", default=None)

    args = ap.parse_args()
    grid = GridSpec()

    if args.cmd == "frames":
        build_frames(args.insat_dir, args.dwr_dir, args.era5_file, args.lightning_grid,
                     _parse_iso(args.start), _parse_iso(args.end), args.frames_dir, grid)
    elif args.cmd == "dataset":
        build_dataset(args.frames_dir, args.dataset_dir)
    elif args.cmd == "selftest":
        _selftest(args.insat_file, args.dwr_file, args.era5_file)


if __name__ == "__main__":
    main()
