from fastapi import APIRouter
from datetime import datetime, timezone
from app.db import fetch_heatmap
from app.model import predictor
from app.updated_model import updated_predictor
from app.schemas.spatial import GeoJSONFeatureCollection, GeoJSONFeature, GeoJSONGeometry, HeatmapFeatureProperties

router = APIRouter()

def fallback_heatmap(time_offset_mins: int) -> GeoJSONFeatureCollection:
    if updated_predictor.available:
        try:
            prediction = updated_predictor.predict_sample_frames(time_offset_mins)
            probabilities = prediction["lightning_probability"]
            height, width = len(probabilities), len(probabilities[0])
            # The training grid is centred on the Cherrapunji DWR domain.
            lat_min, lat_max, lon_min, lon_max = 23.11, 27.43, 89.35, 94.12
            # Keep enough samples for the client-side heatmap to interpolate the
            # model field instead of revealing the training grid as tiles.
            step = 2
            features = []
            for row in range(0, height, step):
                for col in range(0, width, step):
                    block = [line[col:col + step] for line in probabilities[row:row + step]]
                    prob = round(max(max(line) for line in block), 2)
                    risk = "HIGH" if prob > 0.70 else ("MEDIUM" if prob > 0.35 else "LOW")
                    south = lat_min + (lat_max - lat_min) * row / height
                    north = lat_min + (lat_max - lat_min) * min(row + step, height) / height
                    west = lon_min + (lon_max - lon_min) * col / width
                    east = lon_min + (lon_max - lon_min) * min(col + step, width) / width
                    features.append(GeoJSONFeature(
                        geometry=GeoJSONGeometry(coordinates=[[[west, south], [east, south], [east, north], [west, north], [west, south]]]),
                        properties=HeatmapFeatureProperties(
                            lightning_probability=prob,
                            risk_level=risk,
                            timestamp_offset=f"+{time_offset_mins}m",
                            source="updated-model",
                        ),
                    ))
            return GeoJSONFeatureCollection(features=features)
        except (RuntimeError, ValueError, OSError):
            pass

    features = []
    for lat in range(15, 25, 2):
        for lon in range(75, 85, 2):
            prob = predictor.predict(lat, lon, time_offset_mins)
            risk = "HIGH" if prob > 0.70 else ("MEDIUM" if prob > 0.35 else "LOW")
            
            feature = GeoJSONFeature(
                geometry=GeoJSONGeometry(
                    coordinates=[[
                        [float(lon), float(lat)],
                        [float(lon + 1.8), float(lat)],
                        [float(lon + 1.8), float(lat + 1.8)],
                        [float(lon), float(lat + 1.8)],
                        [float(lon), float(lat)]
                    ]]
                ),
                properties=HeatmapFeatureProperties(
                    lightning_probability=prob,
                    risk_level=risk,
                    timestamp_offset=f"+{time_offset_mins}m",
                    source=predictor.source,
                )
            )
            features.append(feature)

    return GeoJSONFeatureCollection(features=features)


@router.get("/nowcast/heatmap", response_model=GeoJSONFeatureCollection)
async def get_heatmap(time_offset_mins: int = 15):
    if not 0 <= time_offset_mins <= 180:
        return fallback_heatmap(15)

    stored = await fetch_heatmap(time_offset_mins)
    return stored or fallback_heatmap(time_offset_mins)
