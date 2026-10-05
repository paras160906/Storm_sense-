# StormSense Verification Metrics & Baseline Audit Report

**Date**: October 5, 2026  
**Scope**: Read-Only Audit — Metrics Computation, Baseline Veracity, Train/Val/Test Splits & Temporal Leakage  
**Target Files**: `backend/stormsense/stormsense/metrics.py`, `backend/stormsense/stormsense/eval.py`, `backend/stormsense/stormsense/dataset.py`, `backend/stormsense/stormsense/train.py`, `frontend/src/screens/Screen6Performance.tsx`

---

## 1. Item-by-Item Audit Summary

| Item | Topic | Verdict | Primary File:Line Evidence | Minimal Fix Needed |
| :---: | :--- | :---: | :--- | :--- |
| **1** | CSI / POD / FAR Math & Inconsistency | **SUSPICIOUS** *(Mock UI Inconsistency)* | [`metrics.py:12-28`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/metrics.py#L12-L28), [`Screen6Performance.tsx`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/frontend/src/screens/Screen6Performance.tsx) | Align UI mock CSI value or serve metrics dynamically via REST API. |
| **2** | Train / Val / Test Split & Leakage | **SUSPICIOUS** *(Leakage Risk)* | [`build_dataset.py:60-64`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L60-L64), [`dataset.py:40-77`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/dataset.py#L40-L77) | Enforce a 2-hour buffer gap between train, validation, and test timestamp ranges. |
| **3** | Validation Loss Measurement | **OK** | [`train.py:37-51`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/train.py#L37-L51), `models/stormsense.pt` | None required. |
| **4** | Baseline Models (Radar / Sat) | **SUSPICIOUS** *(Mock UI Constants)* | [`Screen6Performance.tsx`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/frontend/src/screens/Screen6Performance.tsx) | Build actual single-modality baseline evaluation scripts (`eval_baselines.py`). |
| **5** | Per-Lead-Time Metric Breakdown | **OK** *(Backend)* / **Missing** *(Frontend)* | [`eval.py:35-37`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/eval.py#L35-L37), [`metrics.py:40-60`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/metrics.py#L40-L60) | Add per-lead-time metric breakdown table to frontend `Screen6Performance.tsx`. |

---

## 2. Detailed Findings & Technical Analysis

### Item 1: CSI, POD, FAR Computation & Mathematical Inconsistency
* **Evidence**:
  * [`metrics.py:12-19`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/metrics.py#L12-L19):
    ```python
    def contingency_counts(prob: torch.Tensor, label: torch.Tensor, threshold: float):
        pred = (prob >= threshold)
        truth = (label >= 0.5)
        hits = (pred & truth).sum()
        misses = (~pred & truth).sum()
        false_alarms = (pred & ~truth).sum()
        ...
    ```
  * [`metrics.py:56-60`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/metrics.py#L56-L60):
    ```python
    "csi": hits / (hits + misses + fa + eps),
    "pod": hits / (hits + misses + eps),
    "far": fa / (hits + fa + eps),
    ```
  * Former `Screen6Performance.tsx` mock values:
    ```typescript
    const METRICS = [
      { label: "Probability of Detection", code: "POD", value: 0.86, ... },
      { label: "False Alarm Ratio",        code: "FAR", value: 0.18, ... },
      { label: "Critical Success Index",   code: "CSI", value: 0.74, ... },
    ];
    ```
* **Analysis**:
  * In `metrics.py`, metrics are computed **pixel-level** across accumulated batch counts per lead time step $lt \in (1, 2, 4, 8, 12)$ and threshold $th$. All three metrics are derived from the **exact SAME contingency table** $(H, M, FA)$.
  * Mathematically, derived from a single contingency table:
    $$\text{CSI} = \frac{1}{\frac{1}{\text{POD}} + \frac{\text{FAR}}{1 - \text{FAR}}}$$
    For $\text{POD} = 0.86$ and $\text{FAR} = 0.18$:
    $$\text{CSI} = \frac{1}{\frac{1}{0.86} + \frac{0.18}{0.82}} = \frac{1}{1.16279 + 0.21951} \approx \mathbf{0.7234}$$
  * **Why mock UI reported 0.74**: The numbers previously displayed in the dashboard were **hardcoded mock constants** created for UI demonstration rather than dynamically loaded from `eval.py`.
* **Verdict**: **SUSPICIOUS (Mock UI Inconsistency)**.
* **Minimal Fix**: Render an "Evaluation Pending" prototype status in `Screen6Performance.tsx` reading true facts from `docs/status.json`.

---

### Item 2: Train / Val / Test Split Strategy & Temporal Leakage
* **Evidence**:
  * [`build_dataset.py:60-64`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L60-L64):
    > *"Split ./dataset/all into ./dataset/train, ./dataset/val, ./dataset/test by time (not randomly — nowcasting labels are temporally correlated...)"*
  * [`dataset.py:24-35`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/dataset.py#L24-L35):
    `StormSenseDataset` loads all `.npz` files present in the specified `--data-dir`.
* **Analysis**:
  * The codebase correctly advises splitting by time rather than random frame sampling.
  * **Temporal Leakage Risk**: Because each sample uses a 6-frame input sequence (`seq_len = 6`, covering 75 minutes of history), if `train` ends at time $T$ and `val` begins at $T + 15\text{m}$ without a buffer gap of at least $6 \times 15\text{m} = 90\text{ minutes}$, the first 5 input frames of the `val` set overlap directly with the last 5 frames of the `train` set.
  * **Test Set**: `eval.py` supports `--data-dir ./dataset/test`. However, there is no automated dataset splitting script enforcing buffer windows.
* **Verdict**: **SUSPICIOUS (Potential Temporal Leakage if splits lack buffer gaps)**.
* **Minimal Fix**: Add a split utility script (`split_dataset.py`) that separates frames chronologically while enforcing a 2-hour buffer gap between train, val, and test partitions.

---

### Item 3: Validation Loss Measurement
* **Evidence**:
  * [`train.py:37-51`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/train.py#L37-L51) (`validate` function)
  * [`train.py:75-82`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/train.py#L75-L82) (Checkpoint saving)
  * `backend/models/stormsense.pt` (Top-level key `best_val_loss = 0.4797855...`)
* **Analysis**:
  * The loss is indeed recorded during `validate()` on the validation split.
  * In `train.py:validate()`, both the heteroscedastic BCE loss (`total_loss`) and the `MetricAccumulator` (CSI/POD/FAR) are evaluated inside the exact same validation loop over the `val_loader` split.
* **Verdict**: **OK**.
* **Minimal Fix**: None required.

---

### Item 4: Single-Source Baseline Models (Radar & Satellite)
* **Evidence**:
  * Former [`Screen6Performance.tsx`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/frontend/src/screens/Screen6Performance.tsx):
    ```typescript
    const COMPARISON = [
      { name: "Radar Only",        csi: 0.61, pod: 0.71, far: 0.28, ... },
      { name: "Satellite Only",    csi: 0.56, pod: 0.66, far: 0.33, ... },
      { name: "StormSense Fusion", csi: 0.74, pod: 0.86, far: 0.18, ... },
    ];
    ```
* **Analysis**:
  * The single-source radar baseline and satellite-only baseline existed **only as hardcoded UI constants** in `Screen6Performance.tsx`.
  * There are no radar-only or satellite-only baseline model files, training scripts, or evaluation modules implemented anywhere in `backend/` or `backend/stormsense/`.
* **Verdict**: **SUSPICIOUS (Mock UI Baselines)**.
* **Minimal Fix**: Implement a baseline evaluation script in `backend/stormsense/eval_baselines.py` (e.g., evaluating `StormSenseNet` with `presence_radar=0` or `presence_insat=0` on the test set) to produce true baseline numbers.

---

### Item 5: Per-Lead-Time Metric Breakdown
* **Evidence**:
  * [`metrics.py:40-60`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/metrics.py#L40-L60) (`MetricAccumulator` stores counts per `(lt, th)` pair)
  * [`eval.py:35-37`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/eval.py#L35-L37):
    ```python
    print(f"{'lead':>8} {'thresh':>7} {'CSI':>6} {'POD':>6} {'FAR':>6}")
    for (lt, th), m in sorted(per_lead.items()):
        print(f"{lt*15:>6}min {th:>7.1f} {m['csi']:>6.3f} {m['pod']:>6.3f} {m['far']:>6.3f}")
    ```
* **Analysis**:
  * **Backend**: `eval.py` **DOES** calculate and print a full per-lead-time (+15m, +30m, +60m, +120m, +180m) and per-threshold breakdown when run.
  * **Frontend**: `Screen6Performance.tsx` formerly displayed only pooled summary cards without rendering a per-lead-time breakdown table.
* **Verdict**: **OK in backend, Missing in Frontend UI**.
* **Minimal Fix**: Render an evaluation pending component in `Screen6Performance.tsx` backed by `docs/status.json`.
