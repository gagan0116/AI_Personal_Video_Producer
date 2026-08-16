from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MatchInfo(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    score: str
    league: str
    season: str
    match_date: str
    data_path: str
    video_first_half: str
    video_second_half: str
    display_title: str
    star_players: List[str] = Field(default_factory=list)


class MatchState(BaseModel):
    match_id: str = ""
    status: str = "idle"  # idle, running, paused, halftime, completed, error
    current_half: int = 1
    current_game_time_ms: int = 0
    current_game_time_display: str = "1 - 00:00"
    progress_percentage: float = 0.0
    total_events_processed: int = 0
    agent_outputs_count: Dict[str, int] = Field(default_factory=lambda: {"fan": 0, "coach": 0, "social": 0})
    latest_event_headline: Optional[str] = None
    is_active: bool = False
