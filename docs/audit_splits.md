# StormSense Dataset Splits & Leakage Audit Report

**Date**: October 5, 2026  
**Scope**: Read-Only Audit — Dataset Splits Enumeration, Temporal Leakage, Label Positive Rates, Checkpoint Metadata & Test Set Veracity  
**Target Files**: `backend/stormsense/stormsense/dataset.py`, `backend/stormsense/stormsense/train.py`, `backend/stormsense/stormsense/eval.py`, `backend/models/stormsense.pt`

---

## 1. Enumeration of Dataset Splits

| Split | Location on Disk | `.npz` Sample Count | Start Timestamp | End Timestamp | Distinct Calendar Days | Min / Max Consecutive Gap |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **train** | `backend/stormsense/dataset/train` | **25** | `2026-08-19 00:00` | `2026-08-19 06:00` | **1 day** (`2026-08-19`) | $15.0\text{ min} / 15.0\text{ min}$ |
| **val** | `backend/stormsense/dataset/val` | **20** | `2026-08-19 06:15` | `2026-08-19 11:00` | **1 day** (`2026-08-19`) | $15.0\text{ min} / 15.0\text{ min}$ |
| **test** | `backend/stormsense/dataset/test` | **0** *(Does Not Exist)* | N/A | N/A | **0 days** | N/A |
| **all** | `backend/stormsense/dataset/all` | **0** *(Does Not Exist)* | N/A | N/A | **0 days** | N/A |

---

## 2. Overlap & Temporal Leakage Analysis

* **Exact Timestamp Overlaps**: `0` exact matching timestamps between `train` and `val`.
* **Minimum Inter-Split Time Gap**: **$15.0\text{ minutes}$** between `train` end (`2026-08-19 06:00`) and `val` start (`2026-08-19 06:15`).

### Temporal Footprint Interaction Analysis ($|t - s| < 255\text{ min}$):
Each sample has an operational temporal footprint of **$255\text{ minutes}$** ($75\text{ min}$ input sequence history + $180\text{ min}$ forecast label horizon). Two samples interact and share underlying weather state if their timestamps satisfy $|t - s| < 255\text{ minutes}$.

* **Validation Samples Violating Footprint Isolation**: **16 out of 20 validation samples (80.0%)** have $|t - s| < 255\text{ min}$ relative to the training set.
* **Leakage Mechanism**: The first validation sample at `06:15` uses historical input frames from `05:00` to `06:00` (which were included in the training set). Furthermore, its $+15\text{m}$ to $+180\text{m}$ forecast label window overlaps with the future target labels of late training samples.

---

## 3. Label Positive Rates per Split and Lead Step

Pixel-level positive target rates ($\text{label} \ge 0.5$) across lead steps $1, 2, 4, 8, 12$ ($+15\text{m}, +30\text{m}, +60\text{m}, +120\text{m}, +180\text{m}$):

### `train` Split (25 samples)
* **Lead Step 1 (+15 min)**: `label_lightning` = **0.080%**, `label_intensity` = **0.342%**
* **Lead Step 2 (+30 min)**: `label_lightning` = **0.074%**, `label_intensity` = **0.336%**
* **Lead Step 4 (+60 min)**: `label_lightning` = **0.088%**, `label_intensity` = **0.518%**
* **Lead Step 8 (+120 min)**: `label_lightning` = **0.090%**, `label_intensity` = **0.597%**
* **Lead Step 12 (+180 min)**: `label_lightning` = **0.090%**, `label_intensity` = **0.637%**

### `val` Split (20 samples)
* **Lead Step 1 (+15 min)**: `label_lightning` = **0.078%**, `label_intensity` = **0.322%**
* **Lead Step 2 (+30 min)**: `label_lightning` = **0.073%**, `label_intensity` = **0.362%**
* **Lead Step 4 (+60 min)**: `label_lightning` = **0.087%**, `label_intensity` = **0.501%**
* **Lead Step 8 (+120 min)**: `label_lightning` = **0.092%**, `label_intensity` = **0.617%**
* **Lead Step 12 (+180 min)**: `label_lightning` = **0.091%**, `label_intensity` = **0.645%**

### `test` Split
* **0 samples** on disk.

---

## 4. Test Split Usage in Training & Selection

### Code Audit Evidence (`train.py` & `eval.py`):
* [`train.py:64-69`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/train.py#L64-L69):
  ```python
  if val_dir:
      val_ds = StormSenseDataset(val_dir, cfg, train=False)
      val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False, ...)
  ```
* [`train.py:118-125`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/train.py#L118-L125):
  ```python
  if mean_csi > best_csi:
      best_csi = mean_csi
      ...
      torch.save({ ... }, os.path.join(cfg.checkpoint_dir, "best.pt"))
  ```
* [`eval.py:25-31`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/eval.py#L25-L31):
  ```python
  ds = StormSenseDataset(args.data_dir, cfg, train=False)
  ckpt = torch.load(args.checkpoint, map_location=device)
  model.load_state_dict(ckpt["model"])
  ```

### Findings:
`train.py` **NEVER reads or references the test split**. Checkpoint selection (`best.pt`) is governed strictly by `val_loader`. `eval.py` is a standalone post-hoc evaluation script that evaluates `--data-dir ./dataset/test` independently.

---

## 5. Checkpoint Metadata Analysis (`stormsense.pt`)

### Inspected Values (`weights_only=True`):
* `epoch`: **`92`**
* `best_val_loss`: **`0.4797855794429779`**
* `best_csi`: **`0.0007735756500350265`**

### Split & Threshold Derivation:
* **Split**: `best_csi` was computed on the **validation split (`val_dir`)**.
* **Threshold & Lead Time**: `best_csi` is set in `train.py:50-51` as the **mean CSI averaged across all 5 lead steps and all 5 probability thresholds** ($5 \times 5 = 25$ combinations):
  ```python
  # File: backend/stormsense/stormsense/train.py (Lines 50-51)
  mean_csi = sum(m["csi"] for m in metrics.values()) / len(metrics)
  return total_loss / max(n, 1), mean_csi, metrics
  ```

---

## 6. Independent Storm Days Evaluation

* **Count of Independent Storm Days in Test Split**: **0 days** (`dataset/test` directory does not exist on disk).
* **Count of Independent Storm Days in Train/Val Splits**: **1 day** (`2026-08-19`).

> ⚠️ **CRITICAL FLAG (< 5 Independent Storm Days)**:  
> Both the local training/validation dataset (1 day) and test dataset (0 days) are far below the minimum benchmark threshold of **5 independent storm days** (and ideally weeks-to-months of monsoon data). Metrics computed on a single calendar day reflect temporal auto-correlation rather than generalizable meteorological forecasting skill.
