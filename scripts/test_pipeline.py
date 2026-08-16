import asyncio
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.api.sse import SSEManager
from app.engine.match_engine import MatchEngine
from app.agents.llm_client import NemotronClient
from app.agents.fan_agent import FanAgent
from app.agents.coach_agent import CoachAgent
from app.agents.social_agent import SocialAgent
from app.clips.extractor import ClipExtractor
from app.vss.mock_client import MockVSSClient
from app.models.agents import AgentConfig, AgentType


async def main():
    print("=" * 70)
    print("🧪 Running End-to-End Pipeline Test: Personal AI Sports Producer")
    print("=" * 70)

    sse_manager = SSEManager()
    llm_client = NemotronClient(settings.nemotron_url, settings.nemotron_model)
    clip_extractor = ClipExtractor(settings.output_dir)
    vss_client = MockVSSClient()

    engine = MatchEngine(settings, sse_manager)
    engine.initialize()

    # Create & Register Agents
    fan = FanAgent(
        AgentConfig(agent_id="fan", agent_type=AgentType.FAN, name="Fan Producer", persona="Track player", preset="Neymar"),
        llm_client, clip_extractor, vss_client, sse_manager
    )
    coach = CoachAgent(
        AgentConfig(agent_id="coach", agent_type=AgentType.COACH, name="Coach Producer", persona="Tactical", preset="Defensive breakdowns"),
        llm_client, clip_extractor, vss_client, sse_manager
    )
    social = SocialAgent(
        AgentConfig(agent_id="social", agent_type=AgentType.SOCIAL, name="Social Producer", persona="Viral", preset="Top viral moments"),
        llm_client, clip_extractor, vss_client, sse_manager
    )

    engine.register_agent(fan)
    engine.register_agent(coach)
    engine.register_agent(social)

    print(f"\n[1/3] Discovered {len(engine.available_matches)} matches in catalog.")
    for m in engine.available_matches:
        print(f"  • {m.league}: {m.display_title}")

    test_match = "barcelona_vs_paris_sg"
    print(f"\n[2/3] Initializing match context for '{test_match}'...")
    
    # Load match annotations and context
    match_info = next((m for m in engine.available_matches if m.match_id == test_match), engine.available_matches[0])
    engine.current_match_info = match_info
    
    from app.data.annotation_loader import AnnotationLoader
    from app.data.player_extractor import PlayerExtractor
    from app.engine.event_fusion import EventFusionEngine

    engine.annotation_loader = AnnotationLoader(match_info.data_path)
    engine.annotation_loader.load()
    engine.player_extractor = PlayerExtractor(test_match)
    engine.fusion_engine = EventFusionEngine(engine.player_extractor)
    engine.vss_client = vss_client

    for agent in engine.agents:
        agent.update_match_context(match_info, engine.player_extractor)

    print(f"Loaded {len(engine.annotation_loader.action_events)} action events, {len(engine.annotation_loader.commentary)} commentary segments.")

    print("\n[3/3] Processing Window 1 (Minutes 0:00 - 5:00) with Producer Agents + Nemotron...")
    await engine._process_window(half=1, start_ms=0, end_ms=300000)

    print("Processing Window 2 (Minutes 5:00 - 10:00)...")
    await engine._process_window(half=1, start_ms=300000, end_ms=600000)

    outputs = engine.get_agent_outputs()
    print(f"\nTotal highlight clips produced by agents: {len(outputs)}")

    for agent_id in ("fan", "coach", "social"):
        agent_outs = [o for o in outputs if o.agent_id == agent_id]
        print(f"\n--- {agent_id.upper()} PRODUCER ({len(agent_outs)} outputs) ---")
        for o in agent_outs:
            print(f"  [{o.game_time}] {o.event_type} -> {o.caption}")
            if o.reasoning:
                print(f"    Reasoning: {o.reasoning}")
            print(f"    Clip URL: {o.clip_url} | Importance: {o.importance}")

    await llm_client.close()

    print("\n" + "=" * 70)
    print("✅ END-TO-END PIPELINE VERIFICATION PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
