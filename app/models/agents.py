from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    FAN = "fan"
    COACH = "coach"
    SOCIAL = "social"


class AgentConfig(BaseModel):
    agent_id: str
    agent_type: AgentType
    name: str
    persona: str
    preset: str
    custom_input: str = ""
    enabled: bool = True
    system_prompt_override: Optional[str] = None


class AgentOutput(BaseModel):
    output_id: str
    agent_id: str
    agent_type: str
    event_id: str
    game_time: str
    event_type: str
    caption: str
    clip_url: Optional[str] = None
    clip_path: Optional[str] = None
    clip_duration_s: float = 10.0
    players: List[str] = Field(default_factory=list)
    importance: float = 0.0
    reasoning: Optional[str] = None
    timestamp: str = ""
