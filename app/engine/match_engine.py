import asyncio
import os
from typing import List, Dict, Optional, Any

from app.config import Settings
from app.models.events import FusedEvent
from app.models.match import MatchInfo, MatchState
from app.models.agents import AgentOutput
from app.data.annotation_loader import AnnotationLoader, discover_matches
from app.data.player_extractor import PlayerExtractor
from app.engine.match_clock import MatchClock
from app.engine.event_fusion import EventFusionEngine
from app.vss.client import VSSClient
from app.vss.mock_client import MockVSSClient
from app.api.sse import SSEManager


class MatchEngine:
    """
    Central orchestration engine for Personal AI Sports Producer.
    Runs locally on the GN100 DGX Spark.
    """

    def __init__(self, settings: Settings, sse_manager: SSEManager):
        self.settings = settings
        self.sse_manager = sse_manager

        self.annotation_loader: Optional[AnnotationLoader] = None
        self.player_extractor: Optional[PlayerExtractor] = None
        self.fusion_engine: Optional[EventFusionEngine] = None
        self.vss_client = None
        self.clock: Optional[MatchClock] = None

        self.agents: List[Any] = []
        self.available_matches: List[MatchInfo] = []
        self.current_match_info: Optional[MatchInfo] = None

        self.state = MatchState(
            match_id="",
            status="idle",
            current_half=1,
            current_game_time_ms=0,
            current_game_time_display="1 - 00:00",
            progress_percentage=0.0,
            total_events_processed=0,
            agent_outputs_count={"fan": 0, "coach": 0, "social": 0},
            is_active=False
        )

        self._match_task: Optional[asyncio.Task] = None
        self._all_generated_outputs: List[AgentOutput] = []

    def initialize(self):
        """Discover matches and prepare directory paths."""
        os.makedirs(self.settings.output_dir, exist_ok=True)
        for agent_sub in ("fan", "coach", "social"):
            os.makedirs(os.path.join(self.settings.output_dir, agent_sub), exist_ok=True)

        self.available_matches = discover_matches(self.settings.data_dir)
        if not self.available_matches:
            print("[MatchEngine] Warning: No matches discovered at data_dir. Default presets loaded.")

    def register_agent(self, agent: Any):
        """Register a specialized producer agent."""
        self.agents.append(agent)

    async def start_match(self, match_id: str, speed_multiplier: Optional[float] = None) -> bool:
        """Initialize and launch autonomous processing for the given match."""
        # Stop existing run if any
        await self.stop_match()

        match_info = next((m for m in self.available_matches if m.match_id == match_id), None)
        if not match_info:
            # Fallback to first available or create on the fly
            if self.available_matches:
                match_info = self.available_matches[0]
            else:
                return False

        self.current_match_info = match_info
        effective_speed = speed_multiplier or self.settings.match_speed_multiplier

        # 1. Load match annotations & ASR
        self.annotation_loader = AnnotationLoader(match_info.data_path)
        self.annotation_loader.load()

        # 2. Player extraction
        self.player_extractor = PlayerExtractor(match_id)

        # 3. Multi-modal event fusion
        self.fusion_engine = EventFusionEngine(self.player_extractor)

        # 4. Connect to VSS
        if self.settings.vss_enabled:
            self.vss_client = VSSClient(self.settings.vss_url)
            try:
                await self.vss_client.ingest_video(match_info.video_first_half, match_id)
            except Exception as e:
                print(f"[MatchEngine] VSS ingestion fallback: {e}")
        else:
            self.vss_client = MockVSSClient()

        # Update agents with match context & player extractor
        for agent in self.agents:
            if hasattr(agent, "update_match_context"):
                agent.update_match_context(match_info, self.player_extractor)

        # Reset states & outputs
        self._all_generated_outputs.clear()
        self.state = MatchState(
            match_id=match_id,
            status="running",
            current_half=1,
            current_game_time_ms=0,
            current_game_time_display="1 - 00:00",
            progress_percentage=0.0,
            total_events_processed=0,
            agent_outputs_count={a.config.agent_id: 0 for a in self.agents},
            latest_event_headline=f"Kickoff in {match_info.display_title}!",
            is_active=True
        )

        # 5. Initialize match clock
        self.clock = MatchClock(
            window_size_ms=self.settings.window_size_minutes * 60 * 1000,
            speed_multiplier=effective_speed,
            on_window=self._process_window,
            on_tick=self._on_clock_tick
        )

        await self.sse_manager.emit("match:status", self.state.model_dump())

        # Start match loop in background task
        self._match_task = asyncio.create_task(self._run_match_lifecycle())
        return True

    async def _run_match_lifecycle(self):
        """Runs 1st half, halftime transition, 2nd half, and completion."""
        try:
            print(f"[MatchEngine] Started 1st half simulation for {self.state.match_id}")
            await self.clock.run_half(half=1)

            if not self.state.is_active:
                return

            # Halftime pause
            self.state.status = "halftime"
            self.state.latest_event_headline = "Halftime interval reached. Producer agents aggregating statistics."
            await self.sse_manager.emit("match:status", self.state.model_dump())
            await asyncio.sleep(2.5)

            if not self.state.is_active:
                return

            # Second half
            self.state.status = "running"
            self.state.current_half = 2
            await self.sse_manager.emit("match:status", self.state.model_dump())
            print(f"[MatchEngine] Started 2nd half simulation for {self.state.match_id}")
            await self.clock.run_half(half=2)

            # Match completed
            self.state.status = "completed"
            self.state.is_active = False
            self.state.progress_percentage = 100.0
            self.state.latest_event_headline = f"Full Time! Match concluded. Final score: {self.current_match_info.score if self.current_match_info else ''}"
            await self.sse_manager.emit("match:status", self.state.model_dump())
            await self.sse_manager.emit("match:complete", {
                "match_id": self.state.match_id,
                "total_events": self.state.total_events_processed,
                "total_outputs": len(self._all_generated_outputs)
            })
        except asyncio.CancelledError:
            print("[MatchEngine] Match lifecycle cancelled.")
        except Exception as e:
            print(f"[MatchEngine] Exception in match lifecycle: {e}")
            self.state.status = "error"
            await self.sse_manager.emit("match:status", self.state.model_dump())

    async def _on_clock_tick(self, half: int, position_ms: int, display_time: str):
        """Called every clock increment to update UI progress smoothly."""
        self.state.current_half = half
        self.state.current_game_time_ms = position_ms
        self.state.current_game_time_display = display_time
        if self.clock:
            self.state.progress_percentage = self.clock.get_progress_pct()
        
        await self.sse_manager.emit("match:tick", {
            "half": half,
            "game_time": display_time,
            "position_ms": position_ms,
            "progress": self.state.progress_percentage
        })

    async def _process_window(self, half: int, start_ms: int, end_ms: int):
        """
        Processes a single window slice:
        1. Fetch action, camera & ASR events
        2. Query VSS dense captions
        3. Fuse into rich FusedEvents
        4. Broadcast fused events
        5. Trigger all active producer agents concurrently
        """
        if not self.annotation_loader or not self.fusion_engine:
            return

        # 1. Annotations
        actions = self.annotation_loader.get_events_in_window(start_ms, end_ms, half)
        cameras = self.annotation_loader.get_camera_events_in_window(start_ms, end_ms, half)
        commentary = self.annotation_loader.get_commentary_in_window(start_ms, end_ms, half)

        # 2. VSS Captions
        vss_captions: List[Dict[str, Any]] = []
        if self.vss_client:
            vss_captions = await self.vss_client.get_dense_captions(
                self.state.match_id, start_ms, end_ms
            )

        # 3. Video source file
        video_src = ""
        if self.current_match_info:
            video_src = (
                self.current_match_info.video_first_half if half == 1
                else self.current_match_info.video_second_half
            )

        # 4. Fuse events
        fused_events = self.fusion_engine.fuse(
            action_events=actions,
            camera_events=cameras,
            commentary=commentary,
            vss_captions=vss_captions,
            source_file=video_src,
            half=half,
        )

        self.state.total_events_processed += len(fused_events)
        if fused_events:
            top_event = max(fused_events, key=lambda x: x.importance_score)
            self.state.latest_event_headline = f"{top_event.game_time}: {top_event.event_type} ({top_event.team} team)"

        # Broadcast window events
        await self.sse_manager.emit("match:events", {
            "half": half,
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "count": len(fused_events),
            "events": [e.model_dump() for e in fused_events]
        })

        # 5. Dispatch to all active agents concurrently
        if fused_events:
            agent_tasks = []
            for agent in self.agents:
                if agent.config.enabled:
                    agent_tasks.append(self._run_agent_pipeline(agent, fused_events))
            
            if agent_tasks:
                await asyncio.gather(*agent_tasks, return_exceptions=True)

    async def _run_agent_pipeline(self, agent: Any, fused_events: List[FusedEvent]):
        """Run an agent's reasoning & production pipeline, tracking outputs."""
        try:
            new_outputs: List[AgentOutput] = await agent.process_events(fused_events)
            if new_outputs:
                self._all_generated_outputs.extend(new_outputs)
                current_count = self.state.agent_outputs_count.get(agent.config.agent_id, 0)
                self.state.agent_outputs_count[agent.config.agent_id] = current_count + len(new_outputs)
                
                # Emit updated summary counts
                await self.sse_manager.emit("match:counts", {
                    "counts": self.state.agent_outputs_count
                })
        except Exception as e:
            print(f"[MatchEngine] Agent {agent.config.agent_id} execution error: {e}")

    async def pause_match(self):
        if self.clock:
            self.clock.pause()
            self.state.status = "paused"
            await self.sse_manager.emit("match:status", self.state.model_dump())

    async def resume_match(self):
        if self.clock:
            self.clock.resume()
            self.state.status = "running"
            await self.sse_manager.emit("match:status", self.state.model_dump())

    async def stop_match(self):
        self.state.is_active = False
        self.state.status = "idle"
        if self.clock:
            self.clock.stop()
        if self._match_task and not self._match_task.done():
            self._match_task.cancel()
            try:
                await self._match_task
            except asyncio.CancelledError:
                pass
        await self.sse_manager.emit("match:status", self.state.model_dump())

    def update_agent_config(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """Live update an agent's persona, preset or custom input during match."""
        for agent in self.agents:
            if agent.config.agent_id == agent_id:
                if "preset" in updates:
                    agent.config.preset = updates["preset"]
                if "custom_input" in updates:
                    agent.config.custom_input = updates["custom_input"]
                if "enabled" in updates:
                    agent.config.enabled = updates["enabled"]
                if "persona" in updates:
                    agent.config.persona = updates["persona"]
                print(f"[MatchEngine] Updated agent {agent_id} config: {updates}")
                return True
        return False

    def get_agent_outputs(self, agent_id: Optional[str] = None) -> List[AgentOutput]:
        if agent_id:
            return [o for o in self._all_generated_outputs if o.agent_id == agent_id]
        return list(self._all_generated_outputs)
