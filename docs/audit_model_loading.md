# StormSense Model Loading & Inference Verification Audit Report

**Date**: October 5, 2026  
**Scope**: Read-Only Audit — Import Resolution, Checkpoint Weight Loading, Model Inference, Loss Formulation & Lead-Time Analysis  
**Target Files**: `backend/app/updated_model.py`, `backend/models/stormsense.pt`, `backend/models/stormsense.yaml`, `backend/stormsense/stormsense/losses.py`, `backend/stormsense/stormsense/model.py`

---

## 1. Import Resolution & Module Paths (`from stormsense.stormsense.config import load_config`)

### Questions Analyzed:
- Does `backend/stormsense/stormsense/config.py` exist?
- Are `__init__.py` files present?
- Is `backend/` on `sys.path` when running from documented startup commands?

### Findings:
* **File Existence**:
  - `backend/stormsense/stormsense/config.py` **EXISTS** (`True`).
  - `backend/stormsense/stormsense/__init__.py` **EXISTS** (`True`).
  - `backend/stormsense/__init__.py` **DOES NOT EXIST** (`False`).
* **Namespace Resolution**:
  - In Python 3.3+, `stormsense` functions as an **implicit namespace package**.
  - When starting the API via the documented startup command:
    ```bash
    set PYTHONPATH=backend
    python -m uvicorn app.main:app --reload --port 8000
    ```
    or from the `backend/` directory (`PYTHONPATH=.`), `from stormsense.stormsense.config import load_config` **resolves successfully without errors**.
  - *Gotcha*: If started from the project root without setting `PYTHONPATH=backend` (e.g. bare `uvicorn app.main:app`), `stormsense` is not automatically on `sys.path`.

---

## 2. Checkpoint Loading & State Dict Strict Verification (`stormsense.pt`)

### Execution Command:
```python
import torch, os, sys
sys.path.insert(0, 'backend')
from stormsense.stormsense.config import load_config
from stormsense.stormsense.model import StormSenseNet

cfg = load_config('backend/models/stormsense.yaml')
ckpt = torch.load('backend/models/stormsense.pt', map_location='cpu', weights_only=True)
model = StormSenseNet(cfg)
res = model.load_state_dict(ckpt['model'], strict=True)
```

### Results:
1. **`weights_only=True` Load**: **SUCCESS** (`torch.load('models/stormsense.pt', weights_only=True)` loads cleanly without error).
2. **Top-Level Checkpoint Keys**:
   ```python
   ['model', 'optimizer', 'epoch', 'best_csi', 'best_val_loss']
   ```
3. **`load_state_dict(..., strict=True)`**: **SUCCESS**
   - **Missing Keys**: `[]` (0 missing keys)
   - **Unexpected Keys**: `[]` (0 unexpected keys)

---

## 3. Forward Pass Verification on 6 Sample Frames

### Execution Command:
```python
import torch, numpy as np
from pathlib import Path
from stormsense.stormsense.config import load_config
from stormsense.stormsense.model import StormSenseNet

cfg = load_config('backend/models/stormsense.yaml')
ckpt = torch.load('backend/models/stormsense.pt', map_location='cpu', weights_only=True)
model = StormSenseNet(cfg)
model.load_state_dict(ckpt['model'], strict=True)
model.eval()

files = sorted(Path('backend/models/sample_frames').glob('*.npz'))[:6]
arrays = {m: np.stack([np.load(f)[m] for f in files]) for m in ('insat', 'radar', 'era5', 'lightning')}
tensors = {m: torch.from_numpy(arrays[m].astype(np.float32)).unsqueeze(0) for m in ('insat', 'radar', 'era5', 'lightning')}
presence = {m: torch.tensor([1.0]) for m in ('insat', 'radar', 'era5', 'lightning')}

with torch.inference_mode():
    outputs = model(tensors['insat'], tensors['radar'], tensors['era5'], tensors['lightning'], presence)
```

### Output Tensor Shapes & Channel Statistics per Lead Time Horizon:

Total Output Horizons: `5`  
Configured Lead Steps: `(1, 2, 4, 8, 12)`

#### Lead Horizon 0 (+15 min / Step 1):
* **Output Tensor Shape**: `torch.Size([1, 3, 121, 121])`
* **Channel 0 (Lightning Logit)**: `min = -6.8968`, `max = -0.1799`, `mean = -2.7106` | **Sigmoid Prob**: `min = 0.0010`, `max = 0.4551`, `mean = 0.0739`
* **Channel 1 (Intensity Logit)**: `min = -6.5482`, `max = 4.3155`, `mean = -4.7958` | **Sigmoid Prob**: `min = 0.0014`, `max = 0.9868`, `mean = 0.0408`
* **Channel 2 (Raw Log-Var)**: `min = -3.0961`, `max = 0.1769`, `mean = -1.5716` | **Exp(Var)**: `min = 0.0452`, `max = 1.1935`, `mean = 0.2280`

#### Lead Horizon 1 (+30 min / Step 2):
* **Output Tensor Shape**: `torch.Size([1, 3, 121, 121])`
* **Channel 0 (Lightning Logit)**: `min = -8.2634`, `max = -0.3739`, `mean = -2.8932` | **Sigmoid Prob**: `min = 0.0003`, `max = 0.4076`, `mean = 0.0647`
* **Channel 1 (Intensity Logit)**: `min = -7.7697`, `max = 4.3526`, `mean = -4.9672` | **Sigmoid Prob**: `min = 0.0004`, `max = 0.9873`, `mean = 0.0526`
* **Channel 2 (Raw Log-Var)**: `min = -4.8757`, `max = 1.3406`, `mean = -2.3344` | **Exp(Var)**: `min = 0.0076`, `max = 3.8213`, `mean = 0.1577`

#### Lead Horizon 2 (+60 min / Step 4):
* **Output Tensor Shape**: `torch.Size([1, 3, 121, 121])`
* **Channel 0 (Lightning Logit)**: `min = -7.8101`, `max = -0.0705`, `mean = -2.8443` | **Sigmoid Prob**: `min = 0.0004`, `max = 0.4824`, `mean = 0.0686`
* **Channel 1 (Intensity Logit)**: `min = -8.0128`, `max = 4.3060`, `mean = -5.0833` | **Sigmoid Prob**: `min = 0.0003`, `max = 0.9867`, `mean = 0.0501`
* **Channel 2 (Raw Log-Var)**: `min = -5.3047`, `max = 2.0898`, `mean = -2.5793` | **Exp(Var)**: `min = 0.0050`, `max = 8.0831`, `mean = 0.1722`

#### Lead Horizon 3 (+120 min / Step 8):
* **Output Tensor Shape**: `torch.Size([1, 3, 121, 121])`
* **Channel 0 (Lightning Logit)**: `min = -6.9777`, `max = -0.861`, `mean = -3.2532` | **Sigmoid Prob**: `min = 0.0009`, `max = 0.2971`, `mean = 0.0454`
* **Channel 1 (Intensity Logit)**: `min = -6.0672`, `max = 3.7599`, `mean = -4.4030` | **Sigmoid Prob**: `min = 0.0023`, `max = 0.9772`, `mean = 0.0521`
* **Channel 2 (Raw Log-Var)**: `min = -4.2921`, `max = 0.6501`, `mean = -2.4600` | **Exp(Var)**: `min = 0.0137`, `max = 1.9158`, `mean = 0.1244`

#### Lead Horizon 4 (+180 min / Step 12):
* **Output Tensor Shape**: `torch.Size([1, 3, 121, 121])`
* **Channel 0 (Lightning Logit)**: `min = -6.4811`, `max = -0.7827`, `mean = -2.9400` | **Sigmoid Prob**: `min = 0.0015`, `max = 0.3137`, `mean = 0.0577`
* **Channel 1 (Intensity Logit)**: `min = -6.9463`, `max = 3.4916`, `mean = -4.7224` | **Sigmoid Prob**: `min = 0.0010`, `max = 0.9704`, `mean = 0.0490`
* **Channel 2 (Raw Log-Var)**: `min = -4.4740`, `max = 0.7505`, `mean = -2.2632` | **Exp(Var)**: `min = 0.0114`, `max = 2.1180`, `mean = 0.1612`

---

## 4. Definitiveness of Output Channel 2 (Log-Variance vs. Raw Variance)

### Code Quoted from `backend/stormsense/stormsense/losses.py` (Lines 15–16 & 26):
```python
15: light_logit, inten_logit, log_var = out[:, 0], out[:, 1], out[:, 2]
16: var = torch.exp(log_var).clamp(min=1e-3)
...
26: per_pixel = (light_loss + inten_loss) / var + log_var
```

### Code Quoted from `backend/app/updated_model.py` (Lines 84–86):
```python
84: lightning = self._torch.sigmoid(output[0]).cpu().numpy().tolist()
85: intensity = self._torch.sigmoid(output[1]).cpu().numpy().tolist()
86: uncertainty = self._torch.exp(output[2]).cpu().numpy().tolist()
```

### Definitive Conclusion:
Output channel 2 is **DEFINITIVELY LOG-VARIANCE** ($\log \sigma^2$).
Applying `torch.exp(output[2])` to obtain variance/uncertainty is **100% mathematically correct** and perfectly matches the loss formulation in `losses.py`.

---

## 5. Spec Claim Analysis: "15-Minute Intervals" vs. `cfg.lead_times`

### Configured Lead Times in `backend/models/stormsense.yaml`:
```yaml
lead_times:
- 1
- 2
- 4
- 8
- 12
```

### Analysis:
* **Cadence Step Size**: $1\text{ step} = 15\text{ minutes}$.
* **Actual Lead Horizons Output by Model**:
  1. Step $1 \times 15\text{m} = \mathbf{15\text{ minutes}}$ ($+0.25\text{ hours}$)
  2. Step $2 \times 15\text{m} = \mathbf{30\text{ minutes}}$ ($+0.5\text{ hours}$)
  3. Step $4 \times 15\text{m} = \mathbf{60\text{ minutes}}$ ($+1.0\text{ hour}$)
  4. Step $8 \times 15\text{m} = \mathbf{120\text{ minutes}}$ ($+2.0\text{ hours}$)
  5. Step $12 \times 15\text{m} = \mathbf{180\text{ minutes}}$ ($+3.0\text{ hours}$)

### Findings:
The model does **NOT** output every consecutive 15-minute slot up to 3 hours (which would require 12 output horizons: 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180 min).  
Instead, it outputs **5 non-uniform discrete lead horizons** ($+15\text{m}$, $+30\text{m}$, $+1\text{h}$, $+2\text{h}$, $+3\text{h}$). Intermediate lead times (such as $+45\text{m}$ or $+90\text{m}$) are not generated by the neural network unless interpolated.
