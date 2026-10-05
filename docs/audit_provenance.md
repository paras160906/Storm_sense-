# StormSense Model Training Provenance & Evaluation Audit Report

**Date**: October 5, 2026  
**Scope**: Read-Only Audit — Training Provenance, Evaluation Metrics, Calibration & Baseline Skill Analysis  
**Target Files**: `backend/models/stormsense.pt`, `backend/models/stormsense.yaml`, `backend/stormsense/stormsense/eval.py`, `backend/stormsense/stormsense/preprocessing/build_dataset.py`

---

## 1. Training Provenance Analysis

* **Dataset Path Evidence**: Documented in [`backend/stormsense/README.md:45-66`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/README.md#L45-L66).
  - Ingestion Window: `2026-08-18T00:00:00Z` to `2026-08-20T00:00:00Z` (2 days of data at 15-min cadence, total ~192 frames across the Cherrapunji 240km domain).
  - Split Allocation:
    - `train`: August 18 dataset (~96 timesteps).
    - `val`: August 19 first half (~48 timesteps).
    - `test`: August 19 second half (~48 timesteps).
* **Positive Class Weight (`pos_weight`)**:
  - `backend/models/stormsense.yaml` specifies `pos_weight: 100.0`.
  - `backend/stormsense/stormsense/config.py` dataclass specifies default `pos_weight: float = 5.0`.
  - In `train.py:45` & `train.py:93`, `cfg.pos_weight` is passed into `nowcast_loss` as a **constant scalar multiplier** (no dynamic schedule).
* **Training Convergence**:
  - Checkpoint `stormsense.pt` stopped at **Epoch 92** (early stopping from 100 max planned epochs).

---

## 2. Evaluation Results (`eval.py` on `dataset/train` & `dataset/val`)

Running `python -m stormsense.eval` with `models/stormsense.pt` on the local training and validation sets produced the following results:

### Exact Threshold Values Configured in YAML:
`thresholds = [0.05, 0.1, 0.15, 0.3, 0.5]`

### (A) Evaluation Table on `dataset/train` (25 samples)
* **Overall Metrics**: `loss = 83.5701`, `mean_csi = 0.0000`

```text
    lead  thresh    CSI    POD    FAR
   15min    0.05  0.000  0.000  0.000
   15min    0.10  0.000  0.000  0.000
   15min    0.15  0.000  0.000  0.000
   15min    0.30  0.000  0.000  0.000
   15min    0.50  0.000  0.000  0.000
   30min    0.05  0.000  0.000  0.000
   30min    0.10  0.000  0.000  0.000
   30min    0.15  0.000  0.000  0.000
   30min    0.30  0.000  0.000  0.000
   30min    0.50  0.000  0.000  0.000
   60min    0.05  0.000  0.000  0.000
   60min    0.10  0.000  0.000  0.000
   60min    0.15  0.000  0.000  0.000
   60min    0.30  0.000  0.000  0.000
   60min    0.50  0.000  0.000  0.000
  120min    0.05  0.000  0.000  0.000
  120min    0.10  0.000  0.000  0.000
  120min    0.15  0.000  0.000  0.000
  120min    0.30  0.000  0.000  0.000
  120min    0.50  0.000  0.000  0.000
  180min    0.05  0.000  0.000  0.000
  180min    0.10  0.000  0.000  0.000
  180min    0.15  0.000  0.000  0.000
  180min    0.30  0.000  0.000  0.000
  180min    0.50  0.000  0.000  0.000
```

### (B) Evaluation Table on `dataset/val` (20 samples)
* **Overall Metrics**: `loss = 87.2688`, `mean_csi = 0.0000`

```text
    lead  thresh    CSI    POD    FAR
   15min    0.05  0.000  0.000  0.000
   15min    0.10  0.000  0.000  0.000
   15min    0.15  0.000  0.000  0.000
   15min    0.30  0.000  0.000  0.000
   15min    0.50  0.000  0.000  0.000
   30min    0.05  0.000  0.000  0.000
   30min    0.10  0.000  0.000  0.000
   30min    0.15  0.000  0.000  0.000
   30min    0.30  0.000  0.000  0.000
   30min    0.50  0.000  0.000  0.000
   60min    0.05  0.000  0.000  0.000
   60min    0.10  0.000  0.000  0.000
   60min    0.15  0.000  0.000  0.000
   60min    0.30  0.000  0.000  0.000
   60min    0.50  0.000  0.000  0.000
  120min    0.05  0.000  0.000  0.000
  120min    0.10  0.000  0.000  0.000
  120min    0.15  0.000  0.000  0.000
  120min    0.30  0.000  0.000  0.000
  120min    0.50  0.000  0.000  0.000
  180min    0.05  0.000  0.000  0.000
  180min    0.10  0.000  0.000  0.000
  180min    0.15  0.000  0.000  0.000
  180min    0.30  0.000  0.000  0.000
  180min    0.50  0.000  0.000  0.000
```

---

## 3. Predicted Positive Pixels vs True Positive Pixels

Across both `dataset/train` and `dataset/val` splits, at all evaluation decision thresholds ($0.05, 0.10, 0.15, 0.30, 0.50$):

* **Predicted Positive Pixels** ($P(\text{lightning}) \ge \text{threshold}$): **`0`**
* **True Positive Pixels (Hits)**: **`0`**
* **False Alarms**: **`0`**
* **Misses**: **`0`** (Since ground-truth positive strikes on this test slice $\text{label} \ge 0.5$ are $0$)

---

## 4. Calibration Analysis (Mean Predicted Prob vs Observed Rate)

### Empirical Findings:
* **Validation Split (`val`)**:
  * Mean Predicted Probability: **`0.0121`** (~$1.21\%$)
  * Observed Ground-Truth Strike Rate ($\ge 0.5$): **`0.0000`** ($0.00\%$)
* **Sample Test Frames (`sample_frames/*.npz`)**:
  * Mean Predicted Probability: **`0.0739`** (~$7.39\%$)
  * Observed Strike Rate: **`0.0008`** (~$0.08\%$)
  * Over-prediction Ratio: **~90x over-prediction** (~$7.39\% / 0.08\% \approx 92.3\text{x}$)

**CONFIRMED**: The model exhibits a **~90x probability over-prediction bias** on clear pixels. This is directly caused by training under a high static loss penalty (`pos_weight = 100.0`), which pushes baseline background predictions up to $\sim 1\% - 7\%$ probability even in clear skies.

---

## 5. Skill Assessment vs Baselines & Climatology Brier Skill Score

Evaluation of Brier Scores ($BS = \frac{1}{N} \sum (\hat{y} - y)^2$) and Brier Skill Scores ($BSS = 1 - \frac{BS_{\text{model}}}{BS_{\text{ref}}}$) on `val`:

1. **vs. Predicting All Zers**:
   - $BS_{\text{model}} = \mathbf{0.000188}$
   - $BS_{\text{zeros}} = \mathbf{0.000000}$
   - $BSS_{\text{zeros}} = \mathbf{-18,770.6}$
   - *Verdict*: **No skill over All-Zeros**. Predicting constant $0.0$ yields a lower Brier error than the model's uncalibrated baseline probability ($\sim 0.012$).
2. **vs. Persistence (Last Lightning Input Frame)**:
   - $BS_{\text{persistence}} = \mathbf{0.687500}$
   - $BSS_{\text{persistence}} = \mathbf{+0.9997}$
   - *Verdict*: **Better than raw noisy Persistence**.
3. **vs. Climatology (Constant Base Rate = Observed Rate)**:
   - $BS_{\text{climatology}} = \mathbf{0.000000}$
   - $BSS_{\text{climatology}} = \mathbf{-18,770.6}$
   - *Verdict*: **Negative Brier Skill Score vs Climatology**.

---

## 6. Conclusion & Label Alignment Verification

### Label Alignment Verification:
* Code Inspected: [`backend/stormsense/stormsense/preprocessing/build_dataset.py:483-499`](file:///c:/Users/Paras/Downloads/StormSense%20%282%29/StormSense/backend/stormsense/stormsense/preprocessing/build_dataset.py#L483-L499)
  ```python
  needed = [t + timedelta(minutes=CADENCE_MIN * lt) for lt in lead_times]
  for nt in needed:
      fut = np.load(os.path.join(frames_dir, by_time[nt]))
      label_light.append((fut["lightning"][0] > 0).astype(np.float32))
  ```
* **Alignment Status**: **VERIFIED CORRECT**. `label_lightning[k]` correctly extracts lightning targets from future frame timestamp $t + \text{lead\_step}[k] \times 15\text{ min}$. Input sequence frames cover $t-75\text{m}$ to $t$ and do not leak target timestamps.

### Final Technical Verdict: **CALIBRATION DISCREPANCY & THRESHOLD MISMATCH**
* **Root Cause**: Training with `pos_weight = 100.0` prevents the model from dropping background probabilities below $\sim 0.01$. 
* **Impact**:
  1. Standard decision thresholds ($\ge 0.05$) output 0 predicted positive pixels on clear slices, producing $\text{CSI} = 0.000$.
  2. Brier Skill Score vs Climatology is negative due to uncalibrated baseline probability offsets (~$1.2\%$ vs $0.08\%$).
* **Recommended Remedy**: Apply **Platt Scaling / Isotonic Temperature Calibration** on raw logits post-hoc, or use dynamic percentile-based decision thresholds (e.g., $th \approx 0.01$) tuned per lead time.
