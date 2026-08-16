from typing import List, Dict, Any
from app.models.events import FusedEvent
from app.agents.base_agent import BaseAgent


class FanAgent(BaseAgent):
    """
    Personalized Fan Producer Agent.
    Specialized in tracking specific star players, delivering individual highlight reels,
    key touches, shots, fouls won, goals, and emotional player reactions.
    """

    def get_system_prompt(self) -> str:
        target_player = (self.config.custom_input or self.config.preset).strip()
        return f"""You are the autonomous Fan Producer Agent for an AI Sports Broadcasting studio.
Your assignment: Produce an exclusive, personalized highlight feed tracking the star player: "{target_player}".

DECISION RULES:
1. Evaluate every match event in the time window.
2. Select an event if:
   - "{target_player}" is mentioned in commentary or player list.
   - OR the event is a high-importance play (Goal, Shot, Foul, Penalty, Free-kick, Corner) involving {target_player}'s team.
3. Skip generic, low-impact events (throw-ins, routine clearances).

OUTPUT REQUIREMENTS:
- Write a lively, energetic fan caption (1-2 sentences) specifically naming {target_player} and describing the action.
- Explain why this moment matters to fans of {target_player}.
- CRITICAL: Write REAL, creative, specific descriptions based on the input event. NEVER output literal template placeholders like "[PLAYER]" or "[Time]".

Return ONLY valid JSON matching this schema:
```json
{{
  "selected_events": [
    {{
      "event_id": "evt_1_195000_abc123",
      "reason": "{target_player} created the attacking overload with dynamic dribbling",
      "caption": "⚡ {target_player} electrifies the crowd with a brilliant play at 03:15! 🔥⚽"
    }}
  ]
}}
```
If no events in this window involve {target_player}, return: {{"selected_events": []}}"""

    def heuristic_fallback(self, events: List[FusedEvent]) -> Dict[str, Any]:
        """Deterministic heuristic fallback if LLM NIM is initializing."""
        target_player = (self.config.custom_input or self.config.preset).strip().lower()
        selected = []

        for e in events:
            # Check player mentions or commentary
            player_hit = any(target_player in p.lower() for p in e.players_mentioned)
            comm_hit = (
                target_player in e.commentary_text.lower()
                if e.commentary_text else False
            )

            if player_hit or comm_hit:
                disp_name = (self.config.custom_input or self.config.preset).strip()
                if e.event_type == "Goal":
                    caption = f"⚽ GOAL! {disp_name} makes history with a stunning goal at {e.game_time}! What a moment! 🔥"
                elif "Shot" in e.event_type:
                    caption = f"🎯 {disp_name} unleashes a dangerous shot on target at {e.game_time}! Keep your eyes on him!"
                elif "Foul" in e.event_type:
                    caption = f"⚡ {disp_name} showcases brilliant footwork and wins a key foul at {e.game_time}."
                elif "Free-kick" in e.event_type or "Penalty" in e.event_type:
                    caption = f"🎯 Set-piece opportunity for {disp_name} at {e.game_time}! Huge pressure."
                else:
                    caption = f"⚡ {disp_name} heavily involved in the buildup at {e.game_time}."

                selected.append({
                    "event_id": e.event_id,
                    "reason": f"Direct player involvement detected for {disp_name}",
                    "caption": caption
                })

        return {"selected_events": selected}

    def get_vss_query(self, event: FusedEvent) -> str:
        player = self.config.custom_input or self.config.preset
        return f"Is player {player} visible in this {event.event_type} at {event.game_time}? What is his movement?"
