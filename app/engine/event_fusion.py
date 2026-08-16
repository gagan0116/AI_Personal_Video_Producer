import uuid
from typing import List, Optional, Dict, Any

from app.models.events import ActionEvent, CameraEvent, CommentarySegment, FusedEvent
from app.data.player_extractor import PlayerExtractor
from app.engine.importance import calculate_importance


class EventFusionEngine:
    """
    Fuses multi-modal soccer data streams:
    - Structured Action Spotting (Labels-v2)
    - Camera Transitions & Broadcast Replay Links (Labels-cameras)
    - Timestamped Audio Transcripts / ASR (Echoes Whisper)
    - Visual Descriptions / Dense Captions (NVIDIA VSS)
    """

    COMMENTARY_WINDOW_SEC = 20.0  # Search window around event for commentary context

    def __init__(self, player_extractor: Optional[PlayerExtractor] = None):
        self.player_extractor = player_extractor or PlayerExtractor()

    def fuse(
        self,
        action_events: List[ActionEvent],
        camera_events: List[CameraEvent],
        commentary: List[CommentarySegment],
        vss_captions: List[Dict[str, Any]],
        source_file: str,
        half: int,
    ) -> List[FusedEvent]:
        """
        Produce unified, enriched FusedEvents for a specific time slice.
        """
        fused_list: List[FusedEvent] = []

        for action in action_events:
            # Skip invisible events if needed, but keep visible ones
            if action.visibility == "not shown" and action.label not in ("Goal", "Penalty", "Red card"):
                continue

            event_time_sec = action.position / 1000.0

            # 1. Nearby commentary correlation
            nearby_comm = [
                c for c in commentary
                if c.half == half
                and (c.start_time <= event_time_sec + self.COMMENTARY_WINDOW_SEC)
                and (c.end_time >= event_time_sec - self.COMMENTARY_WINDOW_SEC)
            ]
            comm_text = " ".join(c.text for c in nearby_comm) if nearby_comm else None

            # 2. Extract player mentions
            players: List[str] = []
            if comm_text:
                players = self.player_extractor.extract_players(comm_text)

            # 3. Active camera & Replay analysis
            camera_type = self._find_active_camera(action.position, camera_events, half)
            replay_count = self._count_replays(action.position, camera_events, half)

            # 4. Correlate VSS Dense Caption
            vss_desc = self._match_vss_caption(action.position, vss_captions)

            # 5. Composite importance score
            importance = calculate_importance(
                event_type=action.label,
                replay_count=replay_count,
                commentary_text=comm_text
            )

            # 6. Build FusedEvent
            event_id = f"evt_{half}_{action.position}_{uuid.uuid4().hex[:6]}"
            fused = FusedEvent(
                event_id=event_id,
                half=half,
                game_time=action.game_time,
                timestamp_ms=action.position,
                event_type=action.label,
                team=action.team,
                visibility=action.visibility,
                camera_type=camera_type,
                is_replay=False,
                replay_count=replay_count,
                commentary_text=comm_text,
                players_mentioned=players,
                vss_description=vss_desc,
                importance_score=importance,
                source_file=source_file,
            )
            fused_list.append(fused)

        return fused_list

    def _find_active_camera(self, position_ms: int, camera_events: List[CameraEvent], half: int) -> str:
        """Find the camera active during this moment."""
        active = "Main camera center"
        for cam in camera_events:
            if cam.half == half and cam.position <= position_ms:
                active = cam.label
            elif cam.half == half and cam.position > position_ms:
                break
        return active

    def _count_replays(self, position_ms: int, camera_events: List[CameraEvent], half: int) -> int:
        """Count replays linked to this event position."""
        count = 0
        for cam in camera_events:
            if cam.half == half and cam.replay == "replay" and cam.link:
                try:
                    link_pos = int(cam.link.get("position", 0))
                    if abs(link_pos - position_ms) <= 8000:
                        count += 1
                except (ValueError, TypeError):
                    pass
        return count

    def _match_vss_caption(self, position_ms: int, captions: List[Dict[str, Any]]) -> Optional[str]:
        """Find closest VSS dense caption within 12 seconds."""
        if not captions:
            return None

        best_caption = None
        min_diff = 12000

        for cap in captions:
            cap_time = cap.get("timestamp_ms", cap.get("start_ms", 0))
            diff = abs(cap_time - position_ms)
            if diff < min_diff:
                min_diff = diff
                best_caption = cap.get("description") or cap.get("text") or cap.get("caption")

        return best_caption
