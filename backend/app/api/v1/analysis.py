import asyncio
import json
import urllib.error
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class AnalysisRequest(BaseModel):
    cell_id: str
    probability: int
    lightning_probability: int
    intensity: str
    direction: str
    speed: int
    eta: int
    latitude: float
    longitude: float


class AnalysisResponse(BaseModel):
    source: str
    interpretation: str


def fallback_interpretation(request: AnalysisRequest) -> str:
    return (
        f"{request.cell_id} is showing a {request.intensity} convection signal. "
        f"Thunderstorm probability is {request.probability}% with lightning probability "
        f"at {request.lightning_probability}%. The cell is moving {request.direction} "
        f"at {request.speed} km/h and may reach the monitored area in about {request.eta} minutes."
    )


def request_groq(request: AnalysisRequest) -> str:
    prompt = (
        "Write a concise operational weather analysis in 2 sentences for an emergency "
        "dashboard. Do not invent measurements. Explain the risk and recommended urgency "
        f"for storm cell {request.cell_id}. Data: thunderstorm probability "
        f"{request.probability}%, lightning probability {request.lightning_probability}%, "
        f"intensity {request.intensity}, movement {request.direction} at {request.speed} "
        f"km/h, estimated arrival {request.eta} minutes, coordinates "
        f"{request.latitude:.2f}N {request.longitude:.2f}E."
    )
    payload = json.dumps({
        "model": settings.groq_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 140,
    }).encode("utf-8")
    request_url = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "StormSense/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request_url, timeout=12) as response:
        result = json.load(response)
    return result["choices"][0]["message"]["content"].strip()


@router.post("/nowcast/analysis", response_model=AnalysisResponse)
async def generate_analysis(request: AnalysisRequest) -> AnalysisResponse:
    if not settings.groq_api_key:
        return AnalysisResponse(source="local-fallback", interpretation=fallback_interpretation(request))
    try:
        interpretation = await asyncio.to_thread(request_groq, request)
        return AnalysisResponse(source="groq", interpretation=interpretation)
    except (OSError, urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return AnalysisResponse(source="local-fallback", interpretation=fallback_interpretation(request))

