# StormSense Preprocessing & Model Input Audit Report

**Date**: October 5, 2026  
**Scope**: Read-Only Preprocessing Audit — Training vs. Serving Input Pipeline Comparison  
**Target Project**: StormSense Nowcasting System (`backend/stormsense` & `backend/app`)

---

## 1. Executive Summary

This audit compares the data preparation and preprocessing pipelines at **Training Time** vs. **Serving Time** for the 4 input modalities (`insat`, `radar`, `era5`, `lightning`).

* **Overall Pipeline Alignment**: Both training (`build_dataset.py` / `dataset.py`) and serving (`updated_model.py`) ingest **raw physical arrays** without additional feature scaling or z-score normalization. Grid specs ($121 \times 121$), channel orders, sequence frame lengths ($6$ timesteps), and tensor datatypes (`float32`) match across training and serving.
* **Sample Frames Status**: The bundled sample `.npz` frames in `backend/models/sample_frames/` are **raw, un-normalized physical arrays** produced by Phase 1 of `build_dataset.py`. Serving (`predict_sample_frames`) correctly assumes raw inputs.
* **Key Mismatches Identified**: 3 minor discrepancies exist around dynamic radar presence flag derivation, NaN sanitization on upload, and presence-flag loading in `predict_sample_frames`.

---

## 2. Modality-by-Modality Comparison Matrix

The table below summarizes the preprocessing, normalization, and tensor specifications for each modality across Training and Serving pipelines:

| Feature / Attribute | INSAT (7 channels) | DWR Radar (2 channels) | ERA5 (2 channels) | Lightning (1 channel) |
| :--- | :--- | :--- | :--- | :--- |
| **Training Ingestion** | [`build_dataset.py:174-228`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L174-L228) | [`build_dataset.py:264-329`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L264-L329) | [`build_dataset.py:334-367`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L334-L367) | [`fetch_lightning.py:23-38`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/fetch_lightning.py#L23-L38) |
| **Serving Ingestion** | [`updated_model.py:68-74`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L68-L74) | [`updated_model.py:68-74`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L68-L74) | [`updated_model.py:68-74`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L68-L74) | [`updated_model.py:68-74`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L68-L74) |
| **Normalization / Scaling** | Raw physical units (Kelvin ~200-310K, Albedo 0-1, `is_day` 0/1). No min-max or z-score. | Raw dBZ ($-10$ to $+65$); `-999.0` sentinel for out-of-coverage cells. | Raw CAPE & CIN in J/kg ($0$ to $4000+$). No log1p or scaling. | Raw strike counts per 15-min cell (non-negative float). |
| **NaN Handling** | Scatter regrid interpolation + nearest-neighbor fill (`build_dataset.py:140`). Zeroes if missing. | `np.isfinite` filter on gates; out-of-coverage set to `-999.0` sentinel. | `RegularGridInterpolator` spatial/temporal interpolation. | Filled with `0.0` if no strikes or missing API data. |
| **Channel Order** | `[TIR1_K, TIR2_K, MIR_K, WV_K, VIS_alb, BT_diff, is_day]` | `[dBZ CAPPI @ 2.5km, valid_mask]` | `[CAPE, CIN]` | `[lightning]` |
| **Tensor Data Type** | `float16` on disk $\rightarrow$ `float32` PyTorch Tensor | `float16` on disk $\rightarrow$ `float32` PyTorch Tensor | `float16` on disk $\rightarrow$ `float32` PyTorch Tensor | `float16` on disk $\rightarrow$ `float32` PyTorch Tensor |
| **Grid Size** | $121 \times 121$ ($240\text{ km}$ radius @ $4\text{ km}$ res) | $121 \times 121$ ($240\text{ km}$ radius @ $4\text{ km}$ res) | $121 \times 121$ ($240\text{ km}$ radius @ $4\text{ km}$ res) | $121 \times 121$ ($240\text{ km}$ radius @ $4\text{ km}$ res) |
| **Frame Order & Cadence** | 6 frames ($t-75\text{m}$ to $t$), 15-min cadence | 6 frames ($t-75\text{m}$ to $t$), 15-min cadence | 6 frames ($t-75\text{m}$ to $t$), 15-min cadence | 6 frames ($t-75\text{m}$ to $t$), 15-min cadence |
| **Presence Flag Semantics** | `1.0` if file present; `0.0` if file missing or dropped ($p=0.2$) | Dynamically computed: `float(radar[:, 1].sum() > 0)` in `dataset.py:73` | `1.0` by default; `0.0` if dropped ($p=0.2$) | `1.0` if API had data; `0.0` if missing/dropped |
| **Same Transform at Serving?** | **YES** | **NO** *(Presence flag & sentinel handling mismatch)* | **YES** | **YES** |

---

## 3. Detailed Mismatches & Concrete Fixes

### Mismatch 1: Dynamic Radar Presence Flag Computation
* **Training Side**: [`backend/stormsense/stormsense/dataset.py:73`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/dataset.py#L73)
  ```python
  presence["radar"] = float(radar[:, 1].sum() > 0)
  ```
  *Behavior*: Training dynamically evaluates whether radar coverage exists by summing the `valid_mask` channel across all sequence frames. If `valid_mask` is all zero, `presence["radar"]` is set to `0.0`.
* **Serving Side**: [`backend/app/updated_model.py:75-78`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L75-L78)
  ```python
  presence = {
      name: self._torch.tensor([float(arrays.get(f"presence_{name}", 1.0))], device=self._device)
      for name in self.required_inputs
  }
  ```
  *Behavior*: Serving relies on a passive dictionary lookup (`arrays.get("presence_radar", 1.0)`). If a user uploads radar data where `valid_mask` is all zeros without specifying `presence_radar`, serving defaults to `1.0`, passing `presence["radar"] = 1.0` into `PresenceGatedFusion` instead of `0.0`.
* **Concrete Fix**: In `backend/app/updated_model.py` (`_predict`), compute radar presence dynamically if `presence_radar` is not explicitly supplied in `arrays`:
  ```python
  # File: backend/app/updated_model.py (around line 75)
  if "presence_radar" not in arrays and "radar" in arrays:
      radar_arr = arrays["radar"]
      radar_present = float(radar_arr[:, 1].sum() > 0) if radar_arr.ndim == 4 and radar_arr.shape[1] > 1 else 1.0
      arrays["presence_radar"] = radar_present
  ```

---

### Mismatch 2: Sample Frames Presence Flag Loading
* **Training Side**: [`backend/stormsense/stormsense/preprocessing/build_dataset.py:460-462`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L460-L462)
  *Behavior*: Phase 1 frame generation writes scalar float presence flags (`presence_insat`, `presence_radar`, `presence_lightning`) into the generated `.npz` frame files.
* **Serving Side**: [`backend/app/updated_model.py:116-121`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L116-L121) (`predict_sample_frames`)
  *Behavior*: `predict_sample_frames` extracts channel arrays (`insat`, `radar`, `era5`, `lightning`) from `sample_frames/*.npz` files, but omits loading `presence_*` keys from those sample files. Consequently, `_predict` defaults all presence flags to `1.0`.
* **Concrete Fix**: Update `predict_sample_frames` in `backend/app/updated_model.py`:
  ```python
  # File: backend/app/updated_model.py (around line 121)
  with np.load(files[0]) as first_frame:
      for name in self.required_inputs:
          p_name = f"presence_{name}"
          if p_name in first_frame:
              arrays[p_name] = first_frame[p_name].item()
  ```

---

### Mismatch 3: Serving Input Sanitization (NaN / Inf Defense)
* **Training Side**: [`backend/stormsense/stormsense/preprocessing/build_dataset.py:138-147`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L138-L147)
  *Behavior*: Preprocessing explicitly filters non-finite values (`finite = np.isfinite(...)`) and performs nearest-neighbor imputation on invalid pixels.
* **Serving Side**: [`backend/app/updated_model.py:68-74`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/app/updated_model.py#L68-L74)
  *Behavior*: `_predict` casts uploaded arrays to `float32` and passes them directly to PyTorch without validating against `NaN` or `Inf`. If a client posts an `.npz` archive with corrupted pixels containing `NaN`, PyTorch forward propagation outputs `NaN` maps across all lead times.
* **Concrete Fix**: Add a non-finite check and replacement in `backend/app/updated_model.py` (`_predict`):
  ```python
  # File: backend/app/updated_model.py (around line 70)
  for name in self.required_inputs:
      value = arrays[name].astype(np.float32, copy=False)
      if not np.isfinite(value).all():
          value = np.nan_to_num(value, nan=0.0, posinf=0.0, neginf=0.0)
      ...
  ```

---

## 4. Inspection of Sample Frames (`backend/models/sample_frames/*.npz`)

An empirical inspection of `backend/models/sample_frames/20260819_0000.npz` revealed the following statistics:

```text
insat             : dtype=float16, shape=(7, 121, 121), min=-9.6641, max=298.2500, nans=0
radar             : dtype=float16, shape=(2, 121, 121), min=-999.0000, max=55.0000, nans=0
era5              : dtype=float16, shape=(2, 121, 121), min=0.0000, max=795.0000, nans=0
lightning         : dtype=float16, shape=(1, 121, 121), min=0.0000, max=1.0000, nans=0
label_lightning   : dtype=float32, shape=(5, 121, 121), min=0.0000, max=1.0000, nans=0
label_intensity   : dtype=float32, shape=(5, 121, 121), min=0.0000, max=1.0000, nans=0
```

### Findings:
1. **Raw Physical Units**: The sample `.npz` files contain **un-normalized physical values**:
   * `insat`: Brightness Temperatures in Kelvin (~200–300K), Albedo fractions (0–1), and solar elevation flags (0/1).
   * `radar`: Raw reflectivity in dBZ with `-999.0` out-of-coverage sentinel (channel 0) and binary valid mask (channel 1).
   * `era5`: CAPE/CIN in J/kg (0 to 795 J/kg).
   * `lightning`: Binned strike counts per cell.
2. **Serving Path Alignment**: The serving path (`updated_model.py`) **correctly assumes raw physical values**, feeding arrays into `StormSenseNet` without applying secondary scaling. This aligns 100% with the training loop (`dataset.py`).
