"""Optional serving adapter for the PyTorch StormSense nowcasting model."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings


class UpdatedNowcastPredictor:
    """Loads the checkpoint lazily so the regular API works without PyTorch."""

    required_inputs = ("insat", "radar", "era5", "lightning")

    def __init__(self) -> None:
        self._model: Any = None
        self._torch: Any = None
        self._cfg: Any = None
        self._error: str | None = None
        self._sample_predictions: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        checkpoint_path = Path(settings.nowcast_checkpoint_path)
        if not checkpoint_path.is_file():
            self._error = f"checkpoint not found: {checkpoint_path}"
            return
        try:
            import torch
            from stormsense.stormsense.config import load_config
            from stormsense.stormsense.model import StormSenseNet

            device = "cuda" if settings.nowcast_device == "auto" and torch.cuda.is_available() else settings.nowcast_device
            if device == "auto":
                device = "cpu"
            cfg = load_config(settings.nowcast_config_path or None)
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
            state_dict = checkpoint.get("model", checkpoint)
            model = StormSenseNet(cfg).to(device)
            model.load_state_dict(state_dict)
            model.eval()
            self._model, self._torch, self._cfg, self._device = model, torch, cfg, device
        except Exception as exc:  # Keep the rest of the API operational.
            self._error = f"could not load checkpoint: {exc}"

    @property
    def available(self) -> bool:
        return self._model is not None

    @property
    def detail(self) -> str | None:
        return self._error

    def _predict(self, arrays: dict[str, Any], lead_time_mins: int) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError(self._error or "updated model is unavailable")
        if lead_time_mins % 15:
            raise ValueError("lead_time_mins must be a multiple of 15")
        lead_step = lead_time_mins // 15
        if lead_step not in self._cfg.lead_times:
            allowed = [step * 15 for step in self._cfg.lead_times]
            raise ValueError(f"lead_time_mins must be one of {allowed}")

        tensors = {}
        for name in self.required_inputs:
            value = arrays[name].astype(np.float32, copy=False)
            if value.ndim != 4:
                raise ValueError(f"{name} must have shape [sequence, channels, height, width]")
            if value.shape[0] != self._cfg.seq_len:
                raise ValueError(f"{name} must contain {self._cfg.seq_len} frames")
            tensors[name] = self._torch.from_numpy(value).unsqueeze(0).to(self._device)
        presence = {
            name: self._torch.tensor([float(arrays.get(f"presence_{name}", 1.0))], device=self._device)
            for name in self.required_inputs
        }

        with self._torch.inference_mode():
            output = self._model(
                tensors["insat"], tensors["radar"], tensors["era5"], tensors["lightning"], presence
            )[self._cfg.lead_times.index(lead_step)][0]
            lightning = self._torch.sigmoid(output[0]).cpu().numpy().tolist()
            intensity = self._torch.sigmoid(output[1]).cpu().numpy().tolist()
            uncertainty = self._torch.exp(output[2]).cpu().numpy().tolist()
        return {
            "source": "updated-model",
            "lead_time_mins": lead_time_mins,
            "lightning_probability": lightning,
            "intensity_probability": intensity,
            "variance": uncertainty,
        }

    def predict_archive(self, archive: bytes, lead_time_mins: int) -> dict[str, Any]:
        with np.load(BytesIO(archive)) as data:
            missing = [name for name in self.required_inputs if name not in data]
            if missing:
                raise ValueError(f"archive is missing required arrays: {', '.join(missing)}")
            arrays: dict[str, Any] = {name: data[name] for name in self.required_inputs}
            for name in self.required_inputs:
                presence_name = f"presence_{name}"
                if presence_name in data:
                    arrays[presence_name] = data[presence_name].item()
        return self._predict(arrays, lead_time_mins)

    def predict_sample_frames(self, lead_time_mins: int) -> dict[str, Any]:
        """Forecast from the bundled six-frame example sequence, cached per lead time."""
        if lead_time_mins in self._sample_predictions:
            return self._sample_predictions[lead_time_mins]
        frame_dir = Path(settings.nowcast_sample_frames_path)
        files = sorted(frame_dir.glob("*.npz"))[: self._cfg.seq_len]
        if len(files) != self._cfg.seq_len:
            raise RuntimeError(f"expected {self._cfg.seq_len} frame files in {frame_dir}")
        arrays: dict[str, Any] = {}
        for name in self.required_inputs:
            frames = []
            for frame in files:
                with np.load(frame) as data:
                    frames.append(data[name])
            arrays[name] = np.stack(frames)
        result = self._predict(arrays, lead_time_mins)
        self._sample_predictions[lead_time_mins] = result
        return result


updated_predictor = UpdatedNowcastPredictor()
