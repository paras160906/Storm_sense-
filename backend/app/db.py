import json
from typing import Any

import asyncpg

from app.config import settings

pool: asyncpg.Pool | None = None


async def connect() -> None:
    global pool
    try:
        pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
        async with pool.acquire() as connection:
            await connection.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS nowcast_cells (
                    id BIGSERIAL PRIMARY KEY,
                    valid_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    time_offset_mins INTEGER NOT NULL,
                    lightning_probability DOUBLE PRECISION NOT NULL,
                    risk_level TEXT NOT NULL,
                    geom geometry(Polygon, 4326) NOT NULL
                )
                """
            )
            await connection.execute(
                "CREATE INDEX IF NOT EXISTS nowcast_cells_geom_idx ON nowcast_cells USING GIST (geom)"
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS active_alerts (
                    id BIGSERIAL PRIMARY KEY,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    probability DOUBLE PRECISION NOT NULL,
                    issued_at TEXT NOT NULL
                )
                """
            )
    except (OSError, asyncpg.PostgresError):
        pool = None


async def close() -> None:
    if pool:
        await pool.close()


async def fetch_heatmap(time_offset_mins: int) -> Any:
    if not pool:
        return None
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT lightning_probability, risk_level,
                       ST_AsGeoJSON(geom)::json AS geometry
                FROM nowcast_cells
                WHERE time_offset_mins = $1
                ORDER BY id
                """,
                time_offset_mins,
            )
        if not rows:
            return None
        from app.schemas.spatial import GeoJSONFeature, GeoJSONFeatureCollection, HeatmapFeatureProperties

        return GeoJSONFeatureCollection(
            features=[
                GeoJSONFeature(
                    geometry=json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"],
                    properties=HeatmapFeatureProperties(
                        lightning_probability=row["lightning_probability"],
                        risk_level=row["risk_level"],
                        timestamp_offset=f"+{time_offset_mins}m",
                        source="postgis",
                    ),
                )
                for row in rows
            ]
        )
    except asyncpg.PostgresError:
        return None


async def fetch_alerts() -> list[dict[str, Any]]:
    if not pool:
        return []
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                "SELECT district, state, risk_level, probability, issued_at FROM active_alerts ORDER BY probability DESC"
            )
        return [dict(row) for row in rows]
    except asyncpg.PostgresError:
        return []