"""FastAPI routes for the simulation engine."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import json

from ..core.state import SimulationState
from ..core.clock import SimState

router = APIRouter()

# Global simulation state
sim = SimulationState()


class StepRequest(BaseModel):
    torque: Optional[List[float]] = None
    steps: Optional[int] = 1


class ConfigRequest(BaseModel):
    dt: Optional[float] = None
    time_scale: Optional[float] = None


@router.get("/status")
async def get_status():
    """Get current simulation status and state."""
    return sim.get_state()


@router.post("/start")
async def start_simulation():
    """Start the simulation loop."""
    sim.start()
    return {"status": "running", "sim_time": sim.clock.sim_time}


@router.post("/pause")
async def pause_simulation():
    """Pause the simulation loop."""
    sim.pause()
    return {"status": "paused", "sim_time": sim.clock.sim_time}


@router.post("/stop")
async def stop_simulation():
    """Stop and reset the simulation."""
    sim.stop()
    return {"status": "stopped", "sim_time": 0.0}


@router.post("/step")
async def step_simulation(request: StepRequest):
    """Advance the simulation by one or more steps."""
    state = None
    for _ in range(request.steps):
        state = sim.step(torque=request.torque)
    return state


@router.post("/config")
async def configure_simulation(request: ConfigRequest):
    """Update simulation configuration."""
    if request.dt is not None:
        sim.clock.dt = request.dt
    if request.time_scale is not None:
        sim.clock.time_scale = request.time_scale
    return sim.clock.get_status()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state streaming.

    Sends simulation state at each tick when running.
    Accepts commands: {"command": "step", "torque": [x, y, z]}
    """
    await websocket.accept()
    try:
        while True:
            if sim.clock.state == SimState.RUNNING:
                state = sim.step()
                await websocket.send_json(state)
                await asyncio.sleep(sim.clock.dt / sim.clock.time_scale)
            else:
                # Wait for commands when paused/stopped
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.1
                    )
                    msg = json.loads(data)
                    cmd = msg.get("command", "")
                    if cmd == "step":
                        torque = msg.get("torque")
                        state = sim.step(torque=torque)
                        await websocket.send_json(state)
                    elif cmd == "start":
                        sim.start()
                    elif cmd == "pause":
                        sim.pause()
                    elif cmd == "stop":
                        sim.stop()
                except asyncio.TimeoutError:
                    pass
    except WebSocketDisconnect:
        pass
