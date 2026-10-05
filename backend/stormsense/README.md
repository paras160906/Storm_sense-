# StormSense

Multimodal thunderstorm/lightning nowcasting (SIH26072). INSAT-3DR + DWR Cherrapunji + ERA5 CAPE/CIN + lightning strikes -> ConvLSTM/U-Net -> per-lead lightning + intensity probability maps at lead steps +15, +30, +60, +120, +180 min.

## Status & Limitations

- **Region**: Cherrapunji DWR domain (240 km radius).
- **Training Data**: Single-day dataset (2026-08-19, 45 samples total: 25 train + 20 val).
- **Validation & Testing**: No held-out independent test set yet.
- **Calibration**: Output probabilities are currently uncalibrated.
- **Disclaimer**: Outputs are pipeline proof-of-concept demonstrations and are **NOT** validated forecasts. They must **NOT** be used to drive real emergency alerts or operational safety decisions.

## Project structure

```
stormsense/
├── configs/
│   ├── rtx4050.yaml        # 6GB laptop GPU
│   ├── rtx4060.yaml        # 8GB laptop/desktop GPU
│   └── colab_t4.yaml       # Colab T4, 16GB
├── stormsense/
│   ├── config.py           # Config dataclass + YAML loader
│   ├── dataset.py          # StormSenseDataset
│   ├── model.py            # StormSenseNet (encoders -> fusion -> ConvLSTM -> U-Net)
│   ├── losses.py           # heteroscedastic BCE loss
│   ├── metrics.py          # CSI/POD/FAR categorical verification metrics
│   ├── train.py            # training loop: val, checkpointing, early stop, resume
│   ├── eval.py             # standalone checkpoint evaluation
│   └── preprocessing/
│       ├── build_dataset.py     # raw files -> regridded, labeled .npz dataset
│       └── fetch_lightning.py   # OpenWeather lightning API -> gridded strikes
├── requirements.txt
└── checkpoints/            # gitignored — training writes here
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # or conda
pip install -r requirements.txt
```

## 1. Build the dataset (same on either machine)

```bash
# lightning strikes for the domain/window
python -m stormsense.preprocessing.fetch_lightning \
    --api-key $OWM_API_KEY \
    --center-lat 25.268 --center-lon 91.7332 \
    --domain-radius-km 240 --tile-radius-km 45 \
    --start 2026-08-18T00:00:00Z --end 2026-08-19T23:59:59Z \
    --out-dir ./lightning_cache

# phase 1: regrid raw INSAT/DWR/ERA5 onto the common 121x121 grid, per 15-min slot
python -m stormsense.preprocessing.build_dataset frames \
    --insat-dir  ./raw/insat --dwr-dir ./raw/dwr --era5-file ./raw/era5.nc \
    --lightning-grid ./lightning_cache/lightning_grid.npz \
    --start 2026-08-18T00:00:00Z --end 2026-08-20T00:00:00Z \
    --frames-dir ./frames

# phase 2: stamp future-frame labels -> final training set
python -m stormsense.preprocessing.build_dataset dataset \
    --frames-dir ./frames --dataset-dir ./dataset/all
```

Split `./dataset/all` into `./dataset/train`, `./dataset/val`, `./dataset/test` by time (not randomly — nowcasting labels are temporally correlated, a random split leaks the future into training). Enforce a minimum 2-hour buffer gap between splits to prevent sequence overlap.

## 2. Train

**RTX 4050 (local, 6GB):**
```bash
python -m stormsense.train --config configs/rtx4050.yaml \
    --train-dir ./dataset/train --val-dir ./dataset/val
```

**RTX 4060 (local, 8GB):**
```bash
python -m stormsense.train --config configs/rtx4060.yaml \
    --train-dir ./dataset/train --val-dir ./dataset/val
```

**Colab T4 (16GB):**
```python
!git clone <your-repo> stormsense && cd stormsense
!pip install -q -r requirements.txt
from google.colab import drive; drive.mount('/content/drive')
!python -m stormsense.train --config configs/colab_t4.yaml \
    --train-dir /content/dataset/train --val-dir /content/dataset/val
```

## 3. Evaluate

```bash
python -m stormsense.eval --config configs/rtx4060.yaml \
    --checkpoint checkpoints/rtx4060/best.pt --data-dir ./dataset/test
```
Prints CSI/POD/FAR per lead time per probability threshold.

## Structural Design Features

1. **Axial self-attention.** `model.py` runs row-then-column self-attention (`AxialAttention`) on the ConvLSTM's output context for spatial mixing beyond convolution's local receptive field, at O(HW(H+W)) instead of full 2D self-attention's O((HW)²).
2. **Lead-time conditioning.** `UNetDecoder` is one shared decoder conditioned on lead time via FiLM (`LeadTimeFiLM`) instead of five independent heads.
