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
Your assignment: Produce an exclusive, personalized highlight feed tracking: "{target_player}".

DECISION RULES:
1. Evaluate every match event in the time window.
2. Select an event if:
   - "{target_player}" is explicitly listed in `players_mentioned` or the commentary transcript.
   - OR if the event is a high-importance offensive play (Goal, Penalty, Shot, Free-kick) for the player's team and could involve him.
3. Skip irrelevant events (generic throw-ins, opposing substitutions, distant clearances).

OUTPUT REQUIREMENTS:
- Produce an energetic, fan-centric commentary caption (1-2 sentences).
- Highlight the player's contribution, skill, impact, or emotional reaction.
- Return ONLY JSON matching this schema:
{{
  "selected_events": [
    {{
      "event_id": "<exact event_id from input>",
      "reason": "Clear explanation of player's involvement or significance",
      "caption": "⚡ [PLAYER] [Dynamic play description] at [Time]! [Emoji]"
    }}
  ]
}}
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
