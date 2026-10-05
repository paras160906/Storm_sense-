import os
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR.parent / "models" / "sample_frames"
TRAIN_DIR = BASE_DIR / "dataset" / "train"
VAL_DIR = BASE_DIR / "dataset" / "val"

TRAIN_DIR.mkdir(parents=True, exist_ok=True)
VAL_DIR.mkdir(parents=True, exist_ok=True)

sample_files = sorted(SAMPLE_DIR.glob("*.npz"))
print(f"Found {len(sample_files)} base sample frames in {SAMPLE_DIR}")

# Load template frames
base_data = []
for f in sample_files:
    with np.load(f) as data:
        base_data.append({k: data[k] for k in data.files})

# Generate 25 sequential timesteps for train (00:00 to 06:00, 15-min cadence)
np.random.seed(42)

for i in range(25):
    idx = i % len(base_data)
    frame = {}
    for k, v in base_data[idx].items():
        noise = np.random.normal(0, 0.02, size=v.shape).astype(v.dtype) if v.dtype == np.float32 else np.random.normal(0, 0.02, size=v.shape).astype(np.float16)
        frame[k] = np.clip(v + noise, 0, 1)
    
    hh = (i * 15) // 60
    mm = (i * 15) % 60
    filename = f"20260819_{hh:02d}{mm:02d}.npz"
    np.savez_compressed(TRAIN_DIR / filename, **frame)

print(f"Created 25 training frames in {TRAIN_DIR}")

# Generate 20 sequential timesteps for val (06:15 to 11:00)
for i in range(20):
    t_idx = i + 25
    idx = i % len(base_data)
    frame = {}
    for k, v in base_data[idx].items():
        noise = np.random.normal(0, 0.02, size=v.shape).astype(v.dtype) if v.dtype == np.float32 else np.random.normal(0, 0.02, size=v.shape).astype(np.float16)
        frame[k] = np.clip(v + noise, 0, 1)
    
    hh = (t_idx * 15) // 60
    mm = (t_idx * 15) % 60
    filename = f"20260819_{hh:02d}{mm:02d}.npz"
    np.savez_compressed(VAL_DIR / filename, **frame)

print(f"Created 20 validation frames in {VAL_DIR}")
