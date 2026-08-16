from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class EventType(str, Enum):
    KICKOFF = "Kick-off"
    GOAL = "Goal"
    FOUL = "Foul"
    YELLOW_CARD = "Yellow card"
    RED_CARD = "Red card"
    YELLOW_RED_CARD = "Yellow->Red card"
    CORNER = "Corner"
    SUBSTITUTION = "Substitution"
    SHOT_ON_TARGET = "Shots on target"
    SHOT_OFF_TARGET = "Shots off target"
    CLEARANCE = "Clearance"
    BALL_OUT = "Ball out of play"
    OFFSIDE = "Offside"
    INDIRECT_FREE_KICK = "Indirect free-kick"
    DIRECT_FREE_KICK = "Direct free-kick"
    PENALTY = "Penalty"
    THROW_IN = "Throw-in"


class ActionEvent(BaseModel):
    game_time: str = Field(description="Game time string, e.g., '1 - 00:14'")
    label: str = Field(description="Event label category")
    position: int = Field(description="Position in milliseconds from half start")
    team: str = Field(description="'home' or 'away'")
    visibility: str = Field(default="visible", description="'visible' or 'not shown'")
    half: int = Field(default=1, description="1 for first half, 2 for second half")


class CameraEvent(BaseModel):
    game_time: str = Field(description="Game time string, e.g., '1 - 02:45'")
    label: str = Field(description="Camera description, e.g., 'Main camera right', 'Close-up player'")
    position: int = Field(description="Position in milliseconds")
    change_type: str = Field(default="logo", description="Camera transition type")
    replay: str = Field(default="real-time", description="'real-time' or 'replay'")
    link: Optional[Dict[str, Any]] = Field(default=None, description="Linked live event if this is a replay")
    half: int = Field(default=1)


class CommentarySegment(BaseModel):
    start_time: float = Field(description="Segment start in seconds")
    end_time: float = Field(description="Segment end in seconds")
    text: str = Field(description="Transcribed commentary text")
    half: int = Field(default=1)


class FusedEvent(BaseModel):
    event_id: str
    half: int
    game_time: str
    timestamp_ms: int
    event_type: str
    team: str
    visibility: str = "visible"
    camera_type: Optional[str] = None
    is_replay: bool = False
    replay_count: int = 0
    linked_event: Optional[str] = None
    commentary_text: Optional[str] = None
    players_mentioned: List[str] = Field(default_factory=list)
    vss_description: Optional[str] = None
    importance_score: float = 0.0
    source_file: str = ""
