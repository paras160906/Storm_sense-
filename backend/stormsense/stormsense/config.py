"""StormSense config: dataclass + YAML loader.

configs/rtx4060.yaml and configs/colab_t4.yaml override only the fields
that need to differ per-environment (batch size, crop size, workers).
Everything else is shared so the architecture and loss stay identical
across environments — only throughput knobs change.
"""
import yaml
from dataclasses import dataclass, asdict


@dataclass
class Config:
    insat_channels: int = 7
    radar_channels: int = 2
    era5_channels: int = 2
    lightning_channels: int = 1

    base_width: int = 32
    fusion_dim: int = 96
    convlstm_hidden: int = 64
    convlstm_layers: int = 2

    use_axial_attention: bool = True
    axial_heads: int = 4
    lead_time_embed_dim: int = 64

    seq_len: int = 6
    lead_times: tuple = (1, 2, 4, 8, 12)

    crop_size: int = 128
    batch_size: int = 4
    grad_accum_steps: int = 6
    modality_dropout_p: float = 0.2
    num_workers: int = 4

    lr: float = 2e-4
    weight_decay: float = 1e-4
    epochs: int = 40
    amp: bool = True
    grad_checkpoint_convlstm: bool = True
    pos_weight: float = 5.0
    csi_thresholds: tuple = (0.3, 0.5, 0.7)

    val_every: int = 1
    early_stop_patience: int = 8
    checkpoint_dir: str = "checkpoints"
    log_every: int = 20


def load_config(path: str = None) -> Config:
    cfg = Config()
    if path is None:
        return cfg
    with open(path) as f:
        overrides = yaml.safe_load(f) or {}
    for k, v in overrides.items():
        if isinstance(v, list):
            v = tuple(v)
        setattr(cfg, k, v)
    return cfg


def save_config(cfg: Config, path: str):
    with open(path, "w") as f:
        yaml.safe_dump(asdict(cfg), f)
