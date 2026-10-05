from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1 import heatmap, alerts, model, analysis
from app.db import close, connect


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect()
    yield
    await close()


app = FastAPI(title="StormSense API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(heatmap.router, prefix="/api/v1", tags=["Nowcasting"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])
app.include_router(model.router, prefix="/api/v1", tags=["Nowcasting model"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Storm analysis"])

@app.get("/")
def root():
    return {"status": "online", "system": "StormSense Nowcasting Engine"}
