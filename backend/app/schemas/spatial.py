from pydantic import BaseModel
from typing import List


class GeoJSONGeometry(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]


class HeatmapFeatureProperties(BaseModel):
    lightning_probability: float
    risk_level: str
    timestamp_offset: str
    source: str = "fallback"


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: HeatmapFeatureProperties


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


class ModelStatus(BaseModel):
    available: bool
    source: str
    detail: str | None = None
