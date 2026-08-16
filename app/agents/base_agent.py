import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.models.events import FusedEvent
from app.models.agents import AgentConfig, AgentOutput
from app.models.match import MatchInfo
from app.agents.llm_client import NemotronClient
from app.clips.extractor import ClipExtractor
from app.api.sse import SSEManager
from app.data.player_extractor import PlayerExtractor


class BaseAgent:
    """
    Abstract Base Class for autonomous producer agents running under NemoClaw / OpenShell.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: NemotronClient,
        clip_extractor: ClipExtractor,
        vss_client: Any,
        sse_manager: SSEManager,
    ):
        self.config = config
        self.llm = llm_client
        self.clip_extractor = clip_extractor
        self.vss_client = vss_client
        self.sse_manager = sse_manager
        self.match_info: Optional[MatchInfo] = None
        self.player_extractor: Optional[PlayerExtractor] = None
        self.outputs: List[AgentOutput] = []

    def update_match_context(self, match_info: MatchInfo, player_extractor: PlayerExtractor):
        self.match_info = match_info
        self.player_extractor = player_extractor
        self.outputs.clear()

    def get_system_prompt(self) -> str:
        """Override in specialized subclass."""
        raise NotImplementedError

    def heuristic_fallback(self, events: List[FusedEvent]) -> Dict[str, Any]:
        """Override in subclass to provide deterministic fallback if LLM is offline."""
        return {"selected_events": []}

    def format_event_context(self, events: List[FusedEvent]) -> str:
        """Format batch of FusedEvents into clear structured prompt for Nemotron."""
        lines = [
            f"=== MATCH: {self.match_info.display_title if self.match_info else 'Live Match'} ===",
            f"=== AGENT ROLE: {self.config.name} | FOCUS: '{self.config.custom_input or self.config.preset}' ===",
            f"Total events in window: {len(events)}",
            ""
        ]

        for idx, e in enumerate(events, 1):
            players_str = ", ".join(e.players_mentioned) if e.players_mentioned else "None detected"
            lines.append(f"EVENT #{idx} [ID: {e.event_id}]")
            lines.append(f"  • Time: {e.game_time} (Half {e.half}) | Type: {e.event_type} | Team: {e.team}")
            lines.append(f"  • Importance: {e.importance_score:.2f} | Replays: {e.replay_count} | Camera: {e.camera_type or 'Standard'}")
            lines.append(f"  • Players mentioned: {players_str}")
            if e.commentary_text:
                lines.append(f"  • Audio commentary: \"{e.commentary_text[:160]}\"")
            if e.vss_description:
                lines.append(f"  • VSS Visual perception: \"{e.vss_description[:160]}\"")
            lines.append("")

        return "\n".join(lines)

    async def process_events(self, events: List[FusedEvent]) -> List[AgentOutput]:
        """
        Execute the autonomous agent workflow:
        1. Context assembly & prompt preparation
        2. Nemotron 3.5 Lightning reasoning (selection & caption synthesis)
        3. Visual verification with VSS if needed
        4. Broadcast clip extraction via FFmpeg
        5. SSE event emission
        """
        if not events or not self.config.enabled:
            return []

        prompt_context = self.format_event_context(events)
        system_prompt = self.config.system_prompt_override or self.get_system_prompt()

        # Execute LLM reasoning with fallback
        fallback_fn = lambda user_msg: self.heuristic_fallback(events)
        decision = await self.llm.chat_json(
            system_prompt=system_prompt,
            user_message=prompt_context,
            fallback_handler=fallback_fn
        )

        selected_items = decision.get("selected_events", [])
        new_outputs: List[AgentOutput] = []

        for item in selected_items:
            event_id = str(item.get("event_id", "")).strip()
            caption = item.get("caption", "").strip()
            reasoning = item.get("reason", "").strip()

            # 1. Exact event_id match
            target_event = next((e for e in events if e.event_id == event_id), None)
            
            # 2. Partial/substring ID match
            if not target_event and event_id:
                target_event = next((e for e in events if event_id in e.event_id or e.event_id in event_id), None)
            
            # 3. Game time or event type match in caption/reasoning
            if not target_event:
                for e in events:
                    if e.game_time in caption or e.game_time in reasoning or (e.event_type.lower() in caption.lower() and e.importance_score >= 0.7):
                        target_event = e
                        break
            
            # 4. Fallback to first high-importance event
            if not target_event and events:
                target_event = max(events, key=lambda x: x.importance_score)

            if not target_event or not caption:
                continue

            # Optional VSS visual verification / deep Q&A
            if self.vss_client and not target_event.vss_description:
                try:
                    q = self.get_vss_query(target_event)
                    vss_ans = await self.vss_client.ask_video(
                        stream_id=target_event.source_file,
                        timestamp_ms=target_event.timestamp_ms,
                        question=q
                    )
                    if vss_ans:
                        target_event.vss_description = vss_ans
                except Exception:
                    pass

            # Extract video clip segment
            clip_url = await self.clip_extractor.extract(
                source_file=target_event.source_file,
                start_ms=target_event.timestamp_ms,
                end_ms=target_event.timestamp_ms + 6000,
                agent_id=self.config.agent_id,
                event_id=target_event.event_id,
            )

            output = AgentOutput(
                output_id=f"{self.config.agent_id}_{len(self.outputs) + len(new_outputs) + 1:03d}",
                agent_id=self.config.agent_id,
                agent_type=self.config.agent_type.value,
                event_id=target_event.event_id,
                game_time=target_event.game_time,
                event_type=target_event.event_type,
                caption=caption,
                clip_url=clip_url,
                clip_duration_s=10.0,
                players=target_event.players_mentioned,
                importance=target_event.importance_score,
                reasoning=reasoning,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            new_outputs.append(output)
            self.outputs.append(output)

            # Real-time SSE dispatch to web dashboard
            await self.sse_manager.emit("agent:output", output.model_dump())

        return new_outputs

    def get_vss_query(self, event: FusedEvent) -> str:
        return f"Describe the visual action during this {event.event_type} at {event.game_time}."
