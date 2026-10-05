# StormSense

StormSense is a FastAPI + React nowcasting dashboard. The API prefers PostGIS records and a supplied model artifact, then uses deterministic fallback data while either is unavailable.

## Status & Limitations

- **Region**: Monitored domain centered on Cherrapunji DWR (240 km radius).
- **Training Data**: Trained 92 epochs on a single-day dataset (45 samples: 25 train + 20 val) as a pipeline proof-of-concept.
- **Validation & Testing**: No held-out independent test set yet.
- **Calibration**: Output probabilities are currently uncalibrated (~90x baseline over-prediction bias on clear pixels).
- **Operational Disclaimer**: Outputs are pipeline proof-of-concept demonstrations and are **NOT** validated forecasts. They must **NOT** be used to drive real emergency alerts or operational safety decisions.

## Run locally

1. Start PostGIS: `docker compose up -d postgres`
2. Install backend packages: `python -m pip install -r backend/requirements.txt`
3. Start the API: `set PYTHONPATH=backend` then `python -m uvicorn app.main:app --reload --port 8000`
4. Start the frontend: `cd frontend`, `pnpm install`, then `pnpm dev`

Copy `backend/.env.example` to `backend/.env` for database and model settings. Copy `frontend/.env.example` to `frontend/.env` if the API is hosted somewhere other than `localhost:8000`.

## Attach the model

Put the trained `joblib` artifact at `backend/models/stormsense.joblib`, or set `MODEL_PATH` to another path. It must expose `predict()` and accept rows shaped as `[latitude, longitude, time_offset_mins]`, returning probabilities from 0 to 1. The API response identifies whether each result came from `model`, `postgis`, or `fallback`.

The PostGIS tables are created automatically on API startup. Insert GeoJSON-compatible polygons into `nowcast_cells` with SRID 4326 and matching forecast offsets to replace fallback map cells.

## Attach the PyTorch nowcasting model

The updated multimodal model source is included under `backend/stormsense`. The supplied checkpoint (trained 92 epochs on a 45-sample single-day dataset), matching YAML, and six-frame sample sequence are integrated under `backend/models`, so `GET /api/v1/nowcast/model/status` confirms loading without extra setup. Set `NOWCAST_CHECKPOINT_PATH`, `NOWCAST_CONFIG_PATH`, and `NOWCAST_SAMPLE_FRAMES_PATH` to replace them with your production artifacts. The regular heatmap endpoint uses the bundled sequence to show model output for the Cherrapunji domain when PostGIS has no newer records.

For inference, `POST /api/v1/nowcast/model/predict?lead_time_mins=15` with an `.npz` upload containing `insat`, `radar`, `era5`, and `lightning` arrays. Each must be `[6, channels, height, width]`; optional scalar arrays named `presence_insat`, `presence_radar`, `presence_era5`, and `presence_lightning` can mark an unavailable modality. The response contains lightning and intensity probability maps plus variance at discrete lead steps (+15, +30, +60, +120, +180 min). The dashboard's existing latitude/longitude heatmap remains unchanged because it has no multimodal input frames.
