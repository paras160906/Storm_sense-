"""StormSense dataset — loads the per-timestep .npz files produced by
stormsense/preprocessing/build_dataset.py.
"""
import os
import numpy as np
import torch
from torch.utils.data import Dataset

from .config import Config


class StormSenseDataset(Dataset):
    """
    Expects a directory of per-timestep .npz files, each containing:
      insat:       [insat_channels, H, W]  float16
      radar:       [radar_channels, H, W]  float16  (includes valid_mask)
      era5:        [era5_channels, H, W]   float16
      lightning:   [lightning_channels, H, W] float16
      label_lightning:  [len(lead_times), H, W]  float32
      label_intensity:  [len(lead_times), H, W]  float32
    filenames sorted lexicographically == chronological order at fixed 15-min cadence.
    """

    def __init__(self, data_dir: str, cfg: Config, train: bool = True):
        self.data_dir = data_dir
        self.cfg = cfg
        self.train = train
        self.files = sorted(f for f in os.listdir(data_dir) if f.endswith(".npz"))
        assert len(self.files) > cfg.seq_len + max(cfg.lead_times), (
            "Not enough timesteps in data_dir for the configured seq_len + lead_times"
        )

    def __len__(self):
        return len(self.files) - self.cfg.seq_len - max(self.cfg.lead_times)

    def _load(self, idx):
        return np.load(os.path.join(self.data_dir, self.files[idx]))

    def __getitem__(self, idx):
        cfg = self.cfg
        window = [self._load(idx + t) for t in range(cfg.seq_len)]

        insat = np.stack([w["insat"] for w in window]).astype(np.float32)
        radar = np.stack([w["radar"] for w in window]).astype(np.float32)
        era5 = np.stack([w["era5"] for w in window]).astype(np.float32)
        light = np.stack([w["lightning"] for w in window]).astype(np.float32)

        H, W = insat.shape[-2:]
        cs = cfg.crop_size
        if self.train:
            top = np.random.randint(0, max(1, H - cs))
            left = np.random.randint(0, max(1, W - cs))
        else:
            top, left = (H - cs) // 2, (W - cs) // 2

        def crop(x):
            return x[..., top:top + cs, left:left + cs]

        insat, radar, era5, light = map(crop, (insat, radar, era5, light))

        presence = {"insat": 1.0, "radar": 1.0, "era5": 1.0, "lightning": 1.0}
        if self.train:
            if np.random.rand() < cfg.modality_dropout_p:
                insat[:] = 0.0
                presence["insat"] = 0.0
            if np.random.rand() < cfg.modality_dropout_p:
                era5[:] = 0.0
                presence["era5"] = 0.0
            if np.random.rand() < cfg.modality_dropout_p:
                light[:] = 0.0
                presence["lightning"] = 0.0
        # radar presence reflects the real valid_mask channel, not synthetic dropout
        presence["radar"] = float(radar[:, 1].sum() > 0)

        label_light = crop(self._load(idx + cfg.seq_len - 1)["label_lightning"]).astype(np.float32)
        label_inten = crop(self._load(idx + cfg.seq_len - 1)["label_intensity"]).astype(np.float32)

        return {
            "insat": torch.from_numpy(insat),
            "radar": torch.from_numpy(radar),
            "era5": torch.from_numpy(era5),
            "lightning": torch.from_numpy(light),
            "presence": {k: torch.tensor(v) for k, v in presence.items()},
            "label_lightning": torch.from_numpy(label_light),
            "label_intensity": torch.from_numpy(label_inten),
        }


def collate(batch):
    out = {}
    for key in batch[0]:
        if key == "presence":
            out[key] = {m: torch.stack([b["presence"][m] for b in batch]) for m in batch[0]["presence"]}
        else:
            out[key] = torch.stack([b[key] for b in batch])
    return out
