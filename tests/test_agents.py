import pytest
import asyncio
from app.models.agents import AgentConfig, AgentType
from app.models.events import FusedEvent
from app.agents.fan_agent import FanAgent
from app.agents.coach_agent import CoachAgent
from app.agents.social_agent import SocialAgent
from app.agents.llm_client import NemotronClient
from app.clips.extractor import ClipExtractor
from app.vss.mock_client import MockVSSClient
from app.api.sse import SSEManager


@pytest.mark.asyncio
async def test_agent_heuristic_fallback_outputs():
    sse_manager = SSEManager()
    llm_client = NemotronClient("http://mock:8000/v1")
    clip_extractor = ClipExtractor("output")
    vss_client = MockVSSClient()

    fan = FanAgent(
        AgentConfig(agent_id="fan", agent_type=AgentType.FAN, name="Fan Producer", persona="Track player", preset="Neymar"),
        llm_client, clip_extractor, vss_client, sse_manager
    )

    coach = CoachAgent(
        AgentConfig(agent_id="coach", agent_type=AgentType.COACH, name="Coach", persona="Tactical", preset="Defensive"),
        llm_client, clip_extractor, vss_client, sse_manager
    )

    social = SocialAgent(
        AgentConfig(agent_id="social", agent_type=AgentType.SOCIAL, name="Social", persona="Viral", preset="Goals"),
        llm_client, clip_extractor, vss_client, sse_manager
    )

    sample_events = [
        FusedEvent(
            event_id="evt_01",
            half=1,
            game_time="1 - 03:15",
            timestamp_ms=195000,
            event_type="Goal",
            team="home",
            players_mentioned=["Neymar", "Suarez"],
            commentary_text="Neymar crosses and Suarez scores the goal!",
            importance_score=1.0,
            source_file="1_224p.mkv"
        ),
        FusedEvent(
            event_id="evt_02",
            half=1,
            game_time="1 - 02:45",
            timestamp_ms=165000,
            event_type="Offside",
            team="home",
            players_mentioned=["Cavani"],
            commentary_text="Offside trap sprung by Barcelona defense.",
            importance_score=0.45,
            source_file="1_224p.mkv"
        )
    ]

    fan_outs = await fan.process_events(sample_events)
    coach_outs = await coach.process_events(sample_events)
    social_outs = await social.process_events(sample_events)

    assert len(fan_outs) >= 1
    assert any("neymar" in o.caption.lower() for o in fan_outs)

    assert len(coach_outs) >= 1
    assert any("tactical" in o.caption.lower() or "offside" in o.caption.lower() for o in coach_outs)

    assert len(social_outs) >= 1
    assert any("goal" in o.caption.lower() or "scene" in o.caption.lower() for o in social_outs)

    await llm_client.close()
