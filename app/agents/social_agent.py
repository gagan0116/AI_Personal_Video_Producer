from typing import List, Dict, Any
from app.models.events import FusedEvent
from app.agents.base_agent import BaseAgent


class SocialAgent(BaseAgent):
    """
    Autonomous Social Media Producer Agent.
    Specialized in curating viral-worthy, high-engagement broadcast moments,
    generating ready-to-publish short-form video clips with engaging captions and hashtags.
    """

    def get_system_prompt(self) -> str:
        mode = (self.config.custom_input or self.config.preset).strip()
        return f"""You are the viral Social Media Producer Agent for a modern sports media brand.
Your assignment: Discover and package the most exciting, emotionally charged moments targeting: "{mode}".

DECISION RULES:
1. Select peak moments with massive viral engagement potential:
   - Spectacular goals, screamer strikes, and historic comebacks.
   - Red cards, bench drama, controversial refereeing, and VAR/Penalty decisions.
   - Wild stadium celebrations, iconic player gestures, and miraculous saves.
2. Filter criteria: Focus on events with high importance score (>= 0.60), multiple replays, or excited commentary.
3. Be highly selective: Quality over quantity (max 1-2 clips per window).

OUTPUT REQUIREMENTS:
- Produce a viral-ready, high-energy post caption with emojis and relevant hashtags.
- Include a punchy headline that hooks social media viewers immediately.
- Return ONLY JSON matching this schema:
{{
  "selected_events": [
    {{
      "event_id": "<exact event_id from input>",
      "reason": "Why this moment will drive high social engagement/shares",
      "caption": "🔥 [PUNCHY HOOK] [Exciting event description]! 😱⚽ #Hashtag1 #Hashtag2"
    }}
  ]
}}
If no moments meet the virality threshold in this window, return: {{"selected_events": []}}"""

    def heuristic_fallback(self, events: List[FusedEvent]) -> Dict[str, Any]:
        """Deterministic social highlight heuristic fallback."""
        selected = []

        # Sort window events by importance
        high_impact = [
            e for e in sorted(events, key=lambda x: x.importance_score, reverse=True)
            if e.importance_score >= 0.55 or e.event_type in ("Goal", "Penalty", "Red card", "Shots on target")
        ]

        for e in high_impact[:2]:
            if e.event_type == "Goal":
                caption = f"🚨 ABSOLUTE SCENES! UNREAL GOAL at {e.game_time}! The stadium is on fire! 💥⚽🔥 #EpicMoment #Matchday #UCL"
            elif e.event_type == "Penalty":
                caption = f"😱 HIGH DRAMA! PENALTY awarded at {e.game_time}! Nerves of steel needed right here! 🥶⚽ #PenaltyDrama"
            elif e.event_type == "Red card":
                caption = f"🟥 RED CARD SHOCKER! Player sent off at {e.game_time}! Major turning point in this clash! ⚡👀 #RedCard"
            elif "Shot" in e.event_type:
                caption = f"🚀 WHAT A CHANCE! Screamer on goal at {e.game_time}! Inches away from glory! 🤯🧤 #UnrealPlay"
            else:
                caption = f"🔥 Pure intensity at {e.game_time}! This match is delivering everything! ⚡🏆 #FootballVibes"

            selected.append({
                "event_id": e.event_id,
                "reason": f"High viral excitement index for {e.event_type}",
                "caption": caption
            })

        return {"selected_events": selected}

    def get_vss_query(self, event: FusedEvent) -> str:
        return f"Describe the celebration, player emotion, and crowd reaction during this {event.event_type} at {event.game_time}."
