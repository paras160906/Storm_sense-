from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.spatial import ModelStatus
from app.updated_model import updated_predictor

router = APIRouter()


@router.get("/nowcast/model/status", response_model=ModelStatus)
async def model_status():
    return ModelStatus(
        available=updated_predictor.available,
        source="updated-model" if updated_predictor.available else "fallback",
        detail=updated_predictor.detail,
    )


@router.post("/nowcast/model/predict")
async def model_predict(
    frames: UploadFile = File(..., description="NPZ with six frames for insat, radar, era5, and lightning"),
    lead_time_mins: int = 15,
):
    if not updated_predictor.available:
        raise HTTPException(status_code=503, detail=updated_predictor.detail or "Updated model is unavailable")
    if not frames.filename or not frames.filename.endswith(".npz"):
        raise HTTPException(status_code=422, detail="frames must be an .npz archive")
    try:
        return updated_predictor.predict_archive(await frames.read(), lead_time_mins)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
