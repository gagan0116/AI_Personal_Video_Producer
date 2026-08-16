import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.config import settings

router = APIRouter(prefix="/api")


# ── Match Lifecycle Endpoints ──

@router.get("/matches")
async def list_matches(request: Request):
    """List all available SoccerNet matches in the catalog."""
    engine = request.app.state.engine
    return [m.model_dump() for m in engine.available_matches]


@router.post("/match/start")
async def start_match(
    request: Request,
    payload: Dict[str, Any] = Body(default={})
):
    """
    Launch match simulation and multi-agent production.
    Accepts: { match_id: str, speed_multiplier: float }
    """
    engine = request.app.state.engine
    match_id = payload.get("match_id", "barcelona_vs_paris_sg")
    speed = payload.get("speed_multiplier", settings.match_speed_multiplier)

    success = await engine.start_match(match_id=match_id, speed_multiplier=float(speed))
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to start match {match_id}")

    return {
        "success": True,
        "message": f"Match {match_id} started successfully",
        "state": engine.state.model_dump()
    }


@router.post("/match/pause")
async def pause_match(request: Request):
    engine = request.app.state.engine
    await engine.pause_match()
    return {"success": True, "status": engine.state.status}


@router.post("/match/resume")
async def resume_match(request: Request):
    engine = request.app.state.engine
    await engine.resume_match()
    return {"success": True, "status": engine.state.status}


@router.post("/match/stop")
async def stop_match(request: Request):
    engine = request.app.state.engine
    await engine.stop_match()
    return {"success": True, "status": engine.state.status}


@router.get("/match/status")
async def get_match_status(request: Request):
    """Get active match state and progress."""
    engine = request.app.state.engine
    return {
        "state": engine.state.model_dump(),
        "match_info": engine.current_match_info.model_dump() if engine.current_match_info else None
    }


# ── Agent Management Endpoints ──

@router.get("/agents")
async def list_agents(request: Request):
    """List all registered agents, their current configuration, and output counts."""
    engine = request.app.state.engine
    results = []
    for a in engine.agents:
        results.append({
            "config": a.config.model_dump(),
            "output_count": len(a.outputs),
            "latest_outputs": [o.model_dump() for o in a.outputs[-3:]]
        })
    return results


@router.put("/agents/{agent_id}/config")
async def update_agent_config(
    request: Request,
    agent_id: str,
    payload: Dict[str, Any] = Body(...)
):
    """
    Live reconfiguration of an agent's target player, tactical angle, or social mode.
    Supported even while the match is actively processing!
    """
    engine = request.app.state.engine
    updated = engine.update_agent_config(agent_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Broadcast agent update via SSE
    await request.app.state.sse_manager.emit("agent:config_updated", {
        "agent_id": agent_id,
        "config": payload
    })
    return {"success": True, "agent_id": agent_id, "updated": payload}


@router.get("/agents/{agent_id}/outputs")
async def get_agent_outputs(request: Request, agent_id: str):
    """Retrieve full chronological list of outputs produced by a specific agent."""
    engine = request.app.state.engine
    outputs = engine.get_agent_outputs(agent_id=agent_id)
    return [o.model_dump() for o in outputs]


# ── Clip Serving ──

@router.get("/clips/{agent_id}/{filename}")
async def serve_clip(agent_id: str, filename: str):
    """Serve generated MP4 video clip for inline playback."""
    file_path = Path(settings.output_dir) / agent_id / filename
    if not file_path.exists():
        # Check parent folder fallback
        file_path = Path(settings.output_dir) / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Clip not found")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename,
        headers={"Accept-Ranges": "bytes"}
    )


# ── Server-Sent Events (SSE) Stream ──

@router.get("/events/stream")
async def stream_events(request: Request):
    """
    Real-time Server-Sent Events stream delivering match clock ticks,
    new fused events, and producer agent outputs directly to the browser.
    """
    sse_manager: SSEManager = request.app.state.sse_manager
    queue = sse_manager.connect()

    async def event_generator():
        try:
            # Initial state handshake
            engine = request.app.state.engine
            initial_msg = {
                "event": "system:init",
                "data": {
                    "state": engine.state.model_dump(),
                    "match_info": engine.current_match_info.model_dump() if engine.current_match_info else None,
                    "existing_outputs": [o.model_dump() for o in engine._all_generated_outputs]
                }
            }
            yield initial_msg

            while True:
                if await request.is_disconnected():
                    break
                
                # Fetch next event from client queue
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield msg
                except asyncio.TimeoutError:
                    # Heartbeat keepalive
                    yield {"event": "ping", "data": "keepalive"}
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.disconnect(queue)

    return EventSourceResponse(event_generator())
