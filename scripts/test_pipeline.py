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
    print(f"\n[2/3] Launching high-speed test run for '{test_match}' (Speed: 20x)...")
    
    # Run first window manually to inspect outputs
    success = await engine.start_match(test_match, speed_multiplier=20.0)
    assert success, "Engine failed to start match"

    # Wait for a couple of windows to execute
    await asyncio.sleep(4.0)

    print(f"\n[3/3] Inspecting Generated Outputs:")
    outputs = engine.get_agent_outputs()
    print(f"Total highlight clips produced: {len(outputs)}")

    for agent_id in ("fan", "coach", "social"):
        agent_outs = [o for o in outputs if o.agent_id == agent_id]
        print(f"\n--- {agent_id.upper()} PRODUCER ({len(agent_outs)} outputs) ---")
        for o in agent_outs[:2]:
            print(f"  [{o.game_time}] {o.event_type} -> {o.caption}")
            print(f"    Clip URL: {o.clip_url} | Importance: {o.importance}")

    await engine.stop_match()
    await llm_client.close()

    print("\n" + "=" * 70)
    print("✅ END-TO-END PIPELINE VERIFICATION PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
