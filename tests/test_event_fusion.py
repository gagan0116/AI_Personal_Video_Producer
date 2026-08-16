import pytest
from app.engine.event_fusion import EventFusionEngine
from app.data.player_extractor import PlayerExtractor
from app.models.events import ActionEvent, CameraEvent, CommentarySegment


def test_fusion_attaches_commentary_and_players():
    extractor = PlayerExtractor("barcelona_vs_paris_sg")
    fusion = EventFusionEngine(extractor)

    actions = [
        ActionEvent(game_time="1 - 03:15", label="Goal", position=195000, team="home", visibility="visible", half=1)
    ]
    cameras = [
        CameraEvent(game_time="1 - 03:25", label="Spider camera", position=205000, change_type="logo", replay="replay", link={"position": 195000}, half=1)
    ]
    commentary = [
        CommentarySegment(start_time=190.0, end_time=205.0, text="Goal for Barcelona! Luis Suarez nods it home as Neymar cheers!", half=1)
    ]

    fused = fusion.fuse(
        action_events=actions,
        camera_events=cameras,
        commentary=commentary,
        vss_captions=[],
        source_file="1_224p.mkv",
        half=1
    )

    assert len(fused) == 1
    event = fused[0]
    assert event.event_type == "Goal"
    assert event.replay_count == 1
    assert any("suarez" in p.lower() for p in event.players_mentioned) or any("neymar" in p.lower() for p in event.players_mentioned)
    assert event.importance_score >= 0.90
