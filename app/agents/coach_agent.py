from typing import List, Dict, Any
from app.models.events import FusedEvent
from app.agents.base_agent import BaseAgent


class CoachAgent(BaseAgent):
    """
    Tactical Coach & Analyst Producer Agent.
    Specialized in identifying structural breakdowns, defensive spacing, set-piece routines,
    pressing triggers, transition turnovers, and offside discipline.
    """

    def get_system_prompt(self) -> str:
        focus = (self.config.custom_input or self.config.preset).strip()
        return f"""You are the autonomous Tactical Coach & Analyst Agent in an AI Sports Broadcasting studio.
Your assignment: Produce in-depth tactical breakdown clips with coaching insights focusing on: "{focus}".

DECISION RULES:
1. Identify tactically meaningful events:
   - Defensive breakdowns, high press turnovers, transition counters, and space exploitation.
   - Set-piece execution (Corners, Direct/Indirect Free-kicks, Penalties).
   - Defensive discipline (Offsides, Yellow/Red Cards, Tactical fouls, Clearances).
   - Structural adjustments (Substitutions, formation shifts).
2. Prioritize plays with high tactical instructional value or broadcast replays.
3. Ignore superficial events that lack tactical insight.

OUTPUT REQUIREMENTS:
- Produce clinical, analytical coaching commentary (1-2 sentences) dissecting shape, positioning, pressing, or execution.
- CRITICAL: Write REAL, specific tactical insights based on the match situation. NEVER output literal template placeholders like "[GameTime]" or "[Analytical insight...]".

Return ONLY valid JSON matching this schema:
```json
{{
  "selected_events": [
    {{
      "event_id": "evt_1_195000_abc123",
      "reason": "High press trigger exposed space between center-backs",
      "caption": "📋 TACTICAL BREAKDOWN: Defensive line caught stepping up too late, leaving channel runner unmarked in the box."
    }}
  ]
}}
```
If no tactically significant events occur in this window, return: {{"selected_events": []}}"""

    def heuristic_fallback(self, events: List[FusedEvent]) -> Dict[str, Any]:
        """Deterministic tactical heuristic fallback."""
        focus = (self.config.custom_input or self.config.preset).strip().lower()
        selected = []

        tactical_types = {
            "Offside", "Corner", "Direct free-kick", "Indirect free-kick",
            "Yellow card", "Red card", "Substitution", "Clearance", "Penalty", "Foul"
        }

        for e in events:
            is_tactical = (
                e.event_type in tactical_types or
                e.replay_count > 0 or
                e.importance_score >= 0.45
            )

            if is_tactical:
                if e.event_type == "Offside":
                    caption = f"📋 TACTICAL NOTE [{e.game_time}]: Defensive line successfully springs the offside trap, catching the attacker stepping too early."
                elif e.event_type == "Corner":
                    caption = f"📋 SET-PIECE [{e.game_time}]: Zonal marking organization tested on corner delivery into the six-yard box."
                elif e.event_type == "Direct free-kick":
                    caption = f"📋 DANGEROUS SET-PIECE [{e.game_time}]: Wall positioning and goalkeeper sightline critical on direct free-kick."
                elif e.event_type == "Penalty":
                    caption = f"⚠️ CRITICAL BREAKDOWN [{e.game_time}]: Isolated defender beaten inside the 18-yard box, conceding penalty."
                elif e.event_type in ("Yellow card", "Red card"):
                    caption = f"⚠️ DISCIPLINE [{e.game_time}]: {e.event_type} issued following a tactical foul to break up counter-attack."
                elif e.event_type == "Goal":
                    caption = f"📋 GOAL ANALYSIS [{e.game_time}]: Defensive overload exploited in the final third, leaving free runner unmarked."
                else:
                    caption = f"📋 TRANSITION [{e.game_time}]: Tactical engagement in midfield during phase of possession."

                selected.append({
                    "event_id": e.event_id,
                    "reason": f"Tactical pattern observed for {e.event_type}",
                    "caption": caption
                })

        return {"selected_events": selected[:3]}

    def get_vss_query(self, event: FusedEvent) -> str:
        return f"Analyze the team formations, defensive line height, and tactical spacing during this {event.event_type} at {event.game_time}."
