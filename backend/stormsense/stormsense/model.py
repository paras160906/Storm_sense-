"""StormSense multimodal nowcasting model.

Per-modality CNN encoders -> presence-gated attention fusion -> ConvLSTM
temporal stack -> U-Net decoder -> multi-horizon
{lightning-prob, intensity-prob, log-variance} heads.
"""
from typing import List

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import Config


class ConvBlock(nn.Module):
    def __init__(self, c_in, c_out, stride=1):
        super().__init__()
        self.conv = nn.Conv2d(c_in, c_out, 3, stride=stride, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(c_out)
        self.act = nn.SiLU(inplace=True)

    def forward(self, x):
        return self.act(self.bn(self.conv(x)))


class ModalityEncoder(nn.Module):
    def __init__(self, c_in, base_width):
        super().__init__()
        self.stage1 = nn.Sequential(ConvBlock(c_in, base_width), ConvBlock(base_width, base_width))
        self.stage2 = nn.Sequential(ConvBlock(base_width, base_width * 2, stride=2),
                                     ConvBlock(base_width * 2, base_width * 2))
        self.stage3 = nn.Sequential(ConvBlock(base_width * 2, base_width * 4, stride=2),
                                     ConvBlock(base_width * 4, base_width * 4))

    def forward(self, x):
        s1 = self.stage1(x)
        s2 = self.stage2(s1)
        s3 = self.stage3(s2)
        return s1, s2, s3


class PresenceGatedFusion(nn.Module):
    def __init__(self, n_modalities, c_per_modality, fusion_dim):
        super().__init__()
        self.presence_embed = nn.Embedding(2, c_per_modality)
        self.channel_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(c_per_modality * n_modalities, c_per_modality * n_modalities // 4, 1),
            nn.SiLU(inplace=True),
            nn.Conv2d(c_per_modality * n_modalities // 4, c_per_modality * n_modalities, 1),
            nn.Sigmoid(),
        )
        self.project = nn.Conv2d(c_per_modality * n_modalities, fusion_dim, 1)

    def forward(self, feats: List[torch.Tensor], presence: List[torch.Tensor]):
        gated = []
        for f, p in zip(feats, presence):
            gate = self.presence_embed(p.long()).unsqueeze(-1).unsqueeze(-1)
            gated.append(f * torch.sigmoid(gate))
        x = torch.cat(gated, dim=1)
        attn = self.channel_attn(x)
        x = x * attn
        return self.project(x)


class ConvLSTMCell(nn.Module):
    def __init__(self, c_in, c_hidden, kernel_size=3):
        super().__init__()
        pad = kernel_size // 2
        self.conv = nn.Conv2d(c_in + c_hidden, 4 * c_hidden, kernel_size, padding=pad)
        self.c_hidden = c_hidden

    def forward(self, x, state):
        h, c = state
        combined = torch.cat([x, h], dim=1)
        gates = self.conv(combined)
        i, f, o, g = torch.chunk(gates, 4, dim=1)
        i, f, o = torch.sigmoid(i), torch.sigmoid(f), torch.sigmoid(o)
        g = torch.tanh(g)
        c = f * c + i * g
        h = o * torch.tanh(c)
        return h, c

    def init_state(self, batch, h, w, device):
        z = torch.zeros(batch, self.c_hidden, h, w, device=device)
        return z, z


class ConvLSTMStack(nn.Module):
    def __init__(self, c_in, c_hidden, n_layers):
        super().__init__()
        self.layers = nn.ModuleList()
        for i in range(n_layers):
            self.layers.append(ConvLSTMCell(c_in if i == 0 else c_hidden, c_hidden))

    def forward(self, seq, checkpoint=False):
        b, t, c, h, w = seq.shape
        states = [layer.init_state(b, h, w, seq.device) for layer in self.layers]
        out = None
        for step in range(t):
            x = seq[:, step]
            for i, layer in enumerate(self.layers):
                if checkpoint and self.training:
                    h_i, c_i = torch.utils.checkpoint.checkpoint(
                        layer, x, states[i], use_reentrant=False
                    )
                else:
                    h_i, c_i = layer(x, states[i])
                states[i] = (h_i, c_i)
                x = h_i
            out = x
        return out


class AxialAttention(nn.Module):
    """Row-then-column self-attention over the ConvLSTM's output context map.

    This is an effective mechanism for long-range spatial mixing: instead
    of relying purely on convolution/ConvLSTM's local receptive field, every
    pixel gets to attend to every other pixel in its row, then every other
    pixel in its column. Cost is O(H*W*(H+W)) rather than full 2D
    self-attention's O((H*W)^2), which is what makes it viable at the
    bottleneck resolution (H/4 x W/4) on an 8GB-or-less GPU.
    """
    def __init__(self, dim, heads=4):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.row_attn = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.norm2 = nn.LayerNorm(dim)
        self.col_attn = nn.MultiheadAttention(dim, heads, batch_first=True)

    def forward(self, x):
        b, c, h, w = x.shape

        # Row attention: each row's W pixels attend to each other.
        xr = x.permute(0, 2, 3, 1).reshape(b * h, w, c)          # [b*h, w, c]
        xr_n = self.norm1(xr)
        xr = xr + self.row_attn(xr_n, xr_n, xr_n, need_weights=False)[0]
        xr = xr.reshape(b, h, w, c)

        # Column attention: each column's H pixels attend to each other.
        xc = xr.permute(0, 2, 1, 3).reshape(b * w, h, c)         # [b*w, h, c]
        xc_n = self.norm2(xc)
        xc = xc + self.col_attn(xc_n, xc_n, xc_n, need_weights=False)[0]
        xc = xc.reshape(b, w, h, c).permute(0, 3, 2, 1)           # back to [b,c,h,w]
        return xc


class LeadTimeFiLM(nn.Module):
    """Embeds a lead-time index and produces FiLM (scale, shift) params for
    two decoder stages. This is what lets one shared decoder serve every
    lead time — conditions its single decoder on lead time,
    rather than training an independent head per horizon."""
    def __init__(self, n_lead_times, c_stage1, c_stage2, embed_dim=64):
        super().__init__()
        self.embed = nn.Embedding(n_lead_times, embed_dim)
        self.to_film1 = nn.Linear(embed_dim, c_stage1 * 2)
        self.to_film2 = nn.Linear(embed_dim, c_stage2 * 2)

    def forward(self, lead_idx: int, device):
        e = self.embed(torch.tensor([lead_idx], device=device))
        g1, b1 = self.to_film1(e).chunk(2, dim=-1)
        g2, b2 = self.to_film2(e).chunk(2, dim=-1)
        shape1 = lambda t: t.view(1, -1, 1, 1)
        return (shape1(g1), shape1(b1)), (shape1(g2), shape1(b2))


class UNetDecoder(nn.Module):
    """Single shared decoder conditioned on lead time via FiLM (matches
    spatiotemporal nowcasting literature) instead of one independent head per lead time.

    The first upsample+conv stage (dec1) doesn't depend on lead time at all,
    so it runs ONCE per forward pass regardless of how many lead times are
    requested. Only the second stage + final conv re-run per lead time, so
    conditioning on 5 lead times costs far less than 5x a full decoder pass.
    """
    def __init__(self, bottleneck_dim, skip_dims, out_channels_per_head, n_lead_times):
        super().__init__()
        c2, c1 = skip_dims
        self.up1 = nn.ConvTranspose2d(bottleneck_dim, c2, 2, stride=2)
        self.dec1 = nn.Sequential(ConvBlock(c2 * 2, c2), ConvBlock(c2, c2))
        self.up2 = nn.ConvTranspose2d(c2, c1, 2, stride=2)
        self.dec2 = nn.Sequential(ConvBlock(c1 * 2, c1), ConvBlock(c1, c1))
        self.film = LeadTimeFiLM(n_lead_times, c2, c1)
        self.head = nn.Conv2d(c1, out_channels_per_head, 1)
        self.n_lead_times = n_lead_times

    def forward(self, bottleneck, skip2, skip1):
        shared = self.up1(bottleneck)
        if shared.shape[-2:] != skip2.shape[-2:]:
            shared = F.interpolate(shared, size=skip2.shape[-2:], mode="bilinear", align_corners=False)
        shared = torch.cat([shared, skip2], dim=1)
        shared = self.dec1(shared)  # lead-time-independent, computed once

        outputs = []
        for lt_idx in range(self.n_lead_times):
            (g1, b1), (g2, b2) = self.film(lt_idx, bottleneck.device)
            x = shared * (1 + g1) + b1
            x = self.up2(x)
            if x.shape[-2:] != skip1.shape[-2:]:
                x = F.interpolate(x, size=skip1.shape[-2:], mode="bilinear", align_corners=False)
            x = torch.cat([x, skip1], dim=1)
            x = self.dec2(x)
            x = x * (1 + g2) + b2
            outputs.append(self.head(x))
        return outputs


class StormSenseNet(nn.Module):
    def __init__(self, cfg: Config):
        super().__init__()
        bw = cfg.base_width
        self.enc_insat = ModalityEncoder(cfg.insat_channels, bw)
        self.enc_radar = ModalityEncoder(cfg.radar_channels, bw)
        self.enc_era5 = ModalityEncoder(cfg.era5_channels, bw)
        self.enc_light = ModalityEncoder(cfg.lightning_channels, bw)

        c_bottleneck = bw * 4
        self.fusion = PresenceGatedFusion(n_modalities=4, c_per_modality=c_bottleneck,
                                           fusion_dim=cfg.fusion_dim)
        self.convlstm = ConvLSTMStack(cfg.fusion_dim, cfg.convlstm_hidden, cfg.convlstm_layers)

        self.axial_attn = (
            AxialAttention(cfg.convlstm_hidden, heads=cfg.axial_heads)
            if cfg.use_axial_attention else None
        )

        self.decoder = UNetDecoder(
            bottleneck_dim=cfg.convlstm_hidden,
            skip_dims=(bw * 2, bw),
            out_channels_per_head=3,
            n_lead_times=len(cfg.lead_times),
        )
        self.cfg = cfg

    def _encode_modality_seq(self, encoder, x_seq):
        b, t, c, h, w = x_seq.shape
        flat = x_seq.reshape(b * t, c, h, w)
        s1, s2, s3 = encoder(flat)
        unflat = lambda s: s.reshape(b, t, *s.shape[1:])
        return unflat(s1), unflat(s2), unflat(s3)

    def forward(self, insat, radar, era5, lightning, presence):
        i1, i2, i3 = self._encode_modality_seq(self.enc_insat, insat)
        r1, r2, r3 = self._encode_modality_seq(self.enc_radar, radar)
        e1, e2, e3 = self._encode_modality_seq(self.enc_era5, era5)
        l1, l2, l3 = self._encode_modality_seq(self.enc_light, lightning)

        t = i3.shape[1]
        fused_seq = []
        for step in range(t):
            fused = self.fusion(
                [i3[:, step], r3[:, step], e3[:, step], l3[:, step]],
                [presence["insat"], presence["radar"], presence["era5"], presence["lightning"]],
            )
            fused_seq.append(fused)
        fused_seq = torch.stack(fused_seq, dim=1)

        context = self.convlstm(fused_seq, checkpoint=self.cfg.grad_checkpoint_convlstm)
        if self.axial_attn is not None:
            if self.cfg.grad_checkpoint_convlstm and self.training:
                context = torch.utils.checkpoint.checkpoint(
                    self.axial_attn, context, use_reentrant=False
                )
            else:
                context = self.axial_attn(context)

        skip2, skip1 = i2[:, -1], i1[:, -1]
        head_outputs = self.decoder(context, skip2, skip1)
        return head_outputs
