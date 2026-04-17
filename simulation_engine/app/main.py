"""FastAPI application entry point for the CubeSat HIL Simulation Engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

app = FastAPI(
    title="CubeSat HIL Simulation Engine",
    description="High-fidelity orbital physics and environment simulation for Hardware-in-the-Loop testing.",
    version="1.0.0",
)

# Allow CORS for the React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/sim")


@app.get("/")
async def root():
    return {
        "service": "CubeSat HIL Simulation Engine",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
