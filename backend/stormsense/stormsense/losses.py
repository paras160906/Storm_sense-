import torch
import torch.nn.functional as F


def nowcast_loss(head_outputs, label_lightning, label_intensity, pos_weight=5.0):
    """
    head_outputs: list (per lead time) of [B, 3, H, W] -> (lightning_logit, intensity_logit, log_var)
    label_lightning / label_intensity: [B, n_lead_times, H, W]
    Positives weighted higher via pos_weight; log_var gives per-pixel
    heteroscedastic uncertainty weighting (down-weights inherently noisy cells
    instead of letting them dominate the gradient).
    """
    total = 0.0
    for t, out in enumerate(head_outputs):
        light_logit, inten_logit, log_var = out[:, 0], out[:, 1], out[:, 2]
        var = torch.exp(log_var).clamp(min=1e-3)

        light_loss = F.binary_cross_entropy_with_logits(
            light_logit, label_lightning[:, t],
            pos_weight=torch.tensor(pos_weight, device=light_logit.device), reduction="none",
        )
        inten_loss = F.binary_cross_entropy_with_logits(
            inten_logit, label_intensity[:, t],
            pos_weight=torch.tensor(pos_weight, device=inten_logit.device), reduction="none",
        )
        per_pixel = (light_loss + inten_loss) / var + log_var
        total = total + per_pixel.mean()
    return total / len(head_outputs)
