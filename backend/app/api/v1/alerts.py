from fastapi import APIRouter
from app.db import fetch_alerts
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Alert(BaseModel):
    district: str
    state: str
    risk_level: str
    probability: float
    issued_at: str

@router.get("/alerts", response_model=List[Alert])
async def get_active_alerts():
    stored = await fetch_alerts()
    return stored or [
        {"district": "Ranchi", "state": "Jharkhand", "risk_level": "HIGH", "probability": 0.88, "issued_at": "+15m"},
        {"district": "Cuttack", "state": "Odisha", "risk_level": "MEDIUM", "probability": 0.62, "issued_at": "+30m"}
    ]
