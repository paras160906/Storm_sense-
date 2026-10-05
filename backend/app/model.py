from pathlib import Path
import importlib

import numpy as np

from app.config import settings


class Predictor:
    def __init__(self) -> None:
        self._model = None
        model_path = Path(settings.model_path)
        if model_path.exists():
            try:
                joblib = importlib.import_module("joblib")
                self._model = joblib.load(model_path)
            except (OSError, ValueError, ImportError):
                self._model = None

    @property
    def source(self) -> str:
        return "model" if self._model is not None else "fallback"

    def predict(self, latitude: float, longitude: float, offset_mins: int) -> float:
        if self._model is not None:
            value = self._model.predict(np.array([[latitude, longitude, offset_mins]]))[0]
            return round(float(np.clip(value, 0.0, 1.0)), 2)

        # Stable fallback data keeps the map useful while the trained artifact is absent.
        value = 0.49 + 0.28 * np.sin(latitude * 0.7) + 0.19 * np.cos(longitude * 0.6 + offset_mins / 30)
        return round(float(np.clip(value, 0.05, 0.95)), 2)


predictor = Predictor()