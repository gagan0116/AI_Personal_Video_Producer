import os
import sys
import io
from pathlib import Path
from contextlib import asynccontextmanager

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router
from app.api.sse import SSEManager
from app.engine.match_engine import MatchEngine
from app.agents.llm_client import NemotronClient
from app.agents.fan_agent import FanAgent
from app.agents.coach_agent import CoachAgent
from app.agents.social_agent import SocialAgent
from app.clips.extractor import ClipExtractor
from app.vss.client import VSSClient
from app.vss.mock_client import MockVSSClient
from app.models.agents import AgentConfig, AgentType


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup & lifecycle initialization.
    Spawns all microservice clients and producer agents on the GN100 DGX Spark.
    """
    print("=" * 60)
    print(">> Initializing Personal AI Sports Producer on Acer GN100")
    print(f"• Unified Memory Target: DGX Spark 128GB")
    print(f"• LLM Backend: {settings.nemotron_url} ({settings.nemotron_model})")
    print(f"• VSS Backend: {settings.vss_url} (Enabled: {settings.vss_enabled})")
    print(f"• Speed Multiplier: {settings.match_speed_multiplier}x")
    print("=" * 60)

    # 1. SSE Broadcasting Manager
    sse_manager = SSEManager()
    app.state.sse_manager = sse_manager

    # 2. Nemotron Lightning Client
    llm_client = NemotronClient(
        base_url=settings.nemotron_url,
        model=settings.nemotron_model,
        api_key=settings.nemotron_api_key
    )
    is_llm_ready = await llm_client.check_health()
    if is_llm_ready:
        print(f"• LLM Status: ONLINE (Active Model: '{llm_client.model}')")
    else:
        print(f"• LLM Status: OFFLINE (Check if vLLM/NIM is running at {settings.nemotron_url})")
    app.state.llm_client = llm_client

    # 3. Clip Extractor
    clip_extractor = ClipExtractor(output_dir=settings.output_dir)
    app.state.clip_extractor = clip_extractor

    # 4. VSS Client
    if settings.vss_enabled:
        vss_client = VSSClient(base_url=settings.vss_url)
    else:
        vss_client = MockVSSClient()
    app.state.vss_client = vss_client

    # 5. Match Engine
    engine = MatchEngine(settings=settings, sse_manager=sse_manager)
    engine.initialize()
    app.state.engine = engine

    # 6. Initialize the 3 Autonomous Producer Agents
    # Fan Producer
    fan_config = AgentConfig(
        agent_id="fan",
        agent_type=AgentType.FAN,
        name="Fan Producer",
        persona="Track Star Player",
        preset="Neymar",
        custom_input="Neymar",
        enabled=True
    )
    fan_agent = FanAgent(
        config=fan_config,
        llm_client=llm_client,
        clip_extractor=clip_extractor,
        vss_client=vss_client,
        sse_manager=sse_manager
    )

    # Coach Producer
    coach_config = AgentConfig(
        agent_id="coach",
        agent_type=AgentType.COACH,
        name="Tactical Coach Producer",
        persona="Tactical Analysis",
        preset="Defensive breakdowns & high press",
        custom_input="Defensive breakdowns & offside traps",
        enabled=True
    )
    coach_agent = CoachAgent(
        config=coach_config,
        llm_client=llm_client,
        clip_extractor=clip_extractor,
        vss_client=vss_client,
        sse_manager=sse_manager
    )

    # Social Media Producer
    social_config = AgentConfig(
        agent_id="social",
        agent_type=AgentType.SOCIAL,
        name="Social Media Producer",
        persona="Viral & High Engagement Highlights",
        preset="Top viral moments & goals",
        custom_input="Top viral moments & screamers",
        enabled=True
    )
    social_agent = SocialAgent(
        config=social_config,
        llm_client=llm_client,
        clip_extractor=clip_extractor,
        vss_client=vss_client,
        sse_manager=sse_manager
    )

    # Register with Match Engine
    engine.register_agent(fan_agent)
    engine.register_agent(coach_agent)
    engine.register_agent(social_agent)
    app.state.agents = [fan_agent, coach_agent, social_agent]

    print("[Startup] All Producer Agents (Fan, Coach, Social) registered and armed.")
    yield

    # Clean shutdown
    print("[Shutdown] Stopping active match and closing connection pools...")
    await engine.stop_match()
    await llm_client.close()
    if hasattr(vss_client, "close"):
        await vss_client.close()
    print("[Shutdown] AI Sports Producer shutdown complete.")


app = FastAPI(
    title="Personal AI Sports Producer",
    description="Autonomous multi-agent sports broadcast personalization powered by NVIDIA VSS & Nemotron",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for flexible dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)

# Mount frontend directory for static assets
frontend_dir = Path(__file__).parent.parent / "frontend"
frontend_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    """Serve the single-page live sports studio dashboard."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AI Sports Producer API running. Frontend loading..."}
