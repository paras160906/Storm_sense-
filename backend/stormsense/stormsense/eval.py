"""
    python -m stormsense.eval --config configs/rtx4060.yaml \
        --checkpoint checkpoints/rtx4060/best.pt --data-dir ./dataset/test
"""
import argparse
import torch
from torch.utils.data import DataLoader

from .config import load_config
from .dataset import StormSenseDataset, collate
from .model import StormSenseNet
from .train import validate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--data-dir", required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    ds = StormSenseDataset(args.data_dir, cfg, train=False)
    loader = DataLoader(ds, batch_size=cfg.batch_size, shuffle=False,
                         num_workers=cfg.num_workers, collate_fn=collate)

    model = StormSenseNet(cfg).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt["model"])

    loss, mean_csi, per_lead = validate(model, loader, cfg, device)
    print(f"loss={loss:.4f}  mean_csi={mean_csi:.4f}\n")
    print(f"{'lead':>8} {'thresh':>7} {'CSI':>6} {'POD':>6} {'FAR':>6}")
    for (lt, th), m in sorted(per_lead.items()):
        print(f"{lt*15:>6}min {th:>7.1f} {m['csi']:>6.3f} {m['pod']:>6.3f} {m['far']:>6.3f}")


if __name__ == "__main__":
    main()
