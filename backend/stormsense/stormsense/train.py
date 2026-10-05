"""StormSense training entrypoint.

    python -m stormsense.train --config configs/rtx4060.yaml \
        --train-dir ./dataset/train --val-dir ./dataset/val
"""
import argparse
import os
import time

import torch
from torch.utils.data import DataLoader

from .config import Config, load_config, save_config
from .dataset import StormSenseDataset, collate
from .model import StormSenseNet
from .losses import nowcast_loss
from .metrics import MetricAccumulator


def derive_presence(batch, device):
    return {k: v.to(device, non_blocking=True) for k, v in batch["presence"].items()}


def move_batch(batch, device):
    return {
        "insat": batch["insat"].to(device, non_blocking=True),
        "radar": batch["radar"].to(device, non_blocking=True),
        "era5": batch["era5"].to(device, non_blocking=True),
        "lightning": batch["lightning"].to(device, non_blocking=True),
        "label_lightning": batch["label_lightning"].to(device, non_blocking=True),
        "label_intensity": batch["label_intensity"].to(device, non_blocking=True),
        "presence": derive_presence(batch, device),
    }


@torch.no_grad()
def validate(model, loader, cfg, device):
    model.eval()
    acc = MetricAccumulator(cfg.lead_times, cfg.csi_thresholds)
    total_loss, n = 0.0, 0
    for batch in loader:
        b = move_batch(batch, device)
        with torch.autocast(device_type="cuda" if device == "cuda" else "cpu", enabled=cfg.amp):
            outputs = model(b["insat"], b["radar"], b["era5"], b["lightning"], b["presence"])
            loss = nowcast_loss(outputs, b["label_lightning"], b["label_intensity"], cfg.pos_weight)
        total_loss += loss.item()
        n += 1
        acc.update(outputs, b["label_lightning"])
    metrics = acc.compute()
    mean_csi = sum(m["csi"] for m in metrics.values()) / len(metrics)
    return total_loss / max(n, 1), mean_csi, metrics


def train(cfg: Config, train_dir: str, val_dir: str = None, resume: str = None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)
    save_config(cfg, os.path.join(cfg.checkpoint_dir, "config.yaml"))

    train_ds = StormSenseDataset(train_dir, cfg, train=True)
    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True,
                               num_workers=cfg.num_workers, pin_memory=True,
                               drop_last=True, collate_fn=collate)

    val_loader = None
    if val_dir:
        val_ds = StormSenseDataset(val_dir, cfg, train=False)
        val_loader = DataLoader(val_ds, batch_size=cfg.batch_size, shuffle=False,
                                 num_workers=cfg.num_workers, pin_memory=True,
                                 collate_fn=collate)

    model = StormSenseNet(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    scaler = torch.amp.GradScaler(enabled=cfg.amp)

    start_epoch, best_csi, patience_left = 0, -1.0, cfg.early_stop_patience
    if resume and os.path.exists(resume):
        ckpt = torch.load(resume, map_location=device)
        model.load_state_dict(ckpt["model"])
        opt.load_state_dict(ckpt["optimizer"])
        start_epoch = ckpt["epoch"] + 1
        best_csi = ckpt.get("best_csi", -1.0)
        print(f"Resumed from {resume} at epoch {start_epoch}")

    step = 0
    for epoch in range(start_epoch, cfg.epochs):
        model.train()
        opt.zero_grad()
        t0 = time.time()
        for i, batch in enumerate(train_loader):
            b = move_batch(batch, device)
            with torch.autocast(device_type="cuda" if device == "cuda" else "cpu", enabled=cfg.amp):
                outputs = model(b["insat"], b["radar"], b["era5"], b["lightning"], b["presence"])
                loss = nowcast_loss(outputs, b["label_lightning"], b["label_intensity"], cfg.pos_weight)
                loss = loss / cfg.grad_accum_steps

            scaler.scale(loss).backward()
            if (i + 1) % cfg.grad_accum_steps == 0:
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                scaler.step(opt)
                scaler.update()
                opt.zero_grad()

            step += 1
            if step % cfg.log_every == 0:
                print(f"epoch {epoch} step {step} loss {loss.item() * cfg.grad_accum_steps:.4f}")

        print(f"epoch {epoch} done in {time.time() - t0:.0f}s")

        ckpt = {"model": model.state_dict(), "optimizer": opt.state_dict(),
                "epoch": epoch, "best_csi": best_csi}
        torch.save(ckpt, os.path.join(cfg.checkpoint_dir, "last.pt"))

        if val_loader and (epoch + 1) % cfg.val_every == 0:
            val_loss, mean_csi, per_lead = validate(model, val_loader, cfg, device)
            print(f"epoch {epoch} val_loss {val_loss:.4f} mean_csi {mean_csi:.4f}")
            for (lt, th), m in sorted(per_lead.items()):
                print(f"  lead={lt*15:>3}min th={th:.1f}  CSI={m['csi']:.3f} POD={m['pod']:.3f} FAR={m['far']:.3f}")

            if mean_csi > best_csi:
                best_csi = mean_csi
                ckpt["best_csi"] = best_csi
                torch.save(ckpt, os.path.join(cfg.checkpoint_dir, "best.pt"))
                patience_left = cfg.early_stop_patience
            else:
                patience_left -= 1
                if patience_left <= 0:
                    print(f"Early stopping at epoch {epoch} (no CSI improvement for {cfg.early_stop_patience} val checks)")
                    break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None, help="path to configs/rtx4060.yaml or configs/colab_t4.yaml")
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--val-dir", default=None)
    ap.add_argument("--resume", default=None, help="path to a checkpoint (e.g. checkpoints/last.pt)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    train(cfg, args.train_dir, args.val_dir, args.resume)


if __name__ == "__main__":
    main()
