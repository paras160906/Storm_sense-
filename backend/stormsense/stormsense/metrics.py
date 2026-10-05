"""Categorical verification metrics for nowcasting: CSI, POD, FAR, bias.

These are the metrics standard nowcasting models in literature
report (CSI at several probability/intensity thresholds, per lead time).
Without these you can only compare loss curves, which are not comparable
across papers — CSI is.
"""
import torch


@torch.no_grad()
def contingency_counts(prob: torch.Tensor, label: torch.Tensor, threshold: float):
    pred = (prob >= threshold)
    truth = (label >= 0.5)
    hits = (pred & truth).sum()
    misses = (~pred & truth).sum()
    false_alarms = (pred & ~truth).sum()
    correct_neg = (~pred & ~truth).sum()
    return hits, misses, false_alarms, correct_neg


@torch.no_grad()
def csi_pod_far(prob: torch.Tensor, label: torch.Tensor, threshold: float, eps: float = 1e-6):
    hits, misses, fa, _ = contingency_counts(prob, label, threshold)
    csi = hits / (hits + misses + fa + eps)
    pod = hits / (hits + misses + eps)
    far = fa / (hits + fa + eps)
    bias = (hits + fa) / (hits + misses + eps)
    return {"csi": csi.item(), "pod": pod.item(), "far": far.item(), "bias": bias.item()}


class MetricAccumulator:
    """Accumulates hits/misses/false-alarms across batches per (lead_time, threshold)
    so CSI is computed once over the whole val set, not batch-averaged (batch-averaged
    CSI is biased on sparse events like lightning)."""

    def __init__(self, lead_times, thresholds):
        self.lead_times = lead_times
        self.thresholds = thresholds
        self.counts = {(lt, th): torch.zeros(3) for lt in lead_times for th in thresholds}  # hits, misses, fa

    def update(self, head_outputs, label_lightning):
        for t, lt in enumerate(self.lead_times):
            prob = torch.sigmoid(head_outputs[t][:, 0])
            for th in self.thresholds:
                hits, misses, fa, _ = contingency_counts(prob, label_lightning[:, t], th)
                c = self.counts[(lt, th)]
                c[0] += hits.item()
                c[1] += misses.item()
                c[2] += fa.item()

    def compute(self, eps: float = 1e-6):
        out = {}
        for (lt, th), c in self.counts.items():
            hits, misses, fa = c[0].item(), c[1].item(), c[2].item()
            out[(lt, th)] = {
                "csi": hits / (hits + misses + fa + eps),
                "pod": hits / (hits + misses + eps),
                "far": fa / (hits + fa + eps),
            }
        return out
