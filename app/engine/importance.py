from typing import Optional

# Base importance weights across SoccerNet event categories
EVENT_WEIGHTS = {
    "Goal": 1.0,
    "Penalty": 0.95,
    "Red card": 0.90,
    "Yellow->Red card": 0.85,
    "Shots on target": 0.70,
    "Yellow card": 0.60,
    "Direct free-kick": 0.55,
    "Shots off target": 0.50,
    "Corner": 0.45,
    "Foul": 0.40,
    "Indirect free-kick": 0.35,
    "Offside": 0.35,
    "Substitution": 0.30,
    "Clearance": 0.25,
    "Throw-in": 0.10,
    "Kick-off": 0.05,
    "Ball out of play": 0.05,
}

# Excitement commentary indicators
EXCITEMENT_KEYWORDS = [
    "goal", "incredible", "unbelievable", "magnificent", "sensational",
    "spectacular", "what a strike", "masterpiece", "into the net",
    "scores", "screamer", "stunning", "dramatic", "remontada",
    "brilliant", "saved", "denied", "penalty", "red card", "sent off",
    "danger", "chance", "close", "woodwork", "crossbar", "post"
]


def calculate_importance(
    event_type: str,
    replay_count: int = 0,
    commentary_text: Optional[str] = None
) -> float:
    """
    Computes a composite importance score [0.0 - 1.0] for a match event
    taking into account the raw event type, replay recurrence, and emotional
    intensity in the commentary.
    """
    base_score = EVENT_WEIGHTS.get(event_type, 0.30)

    # Replay multiplier: broad evidence that broadcast directors judged this critical
    replay_bonus = min(replay_count * 0.10, 0.25)

    # Commentary excitement detection
    commentary_bonus = 0.0
    if commentary_text:
        text_lower = commentary_text.lower()
        keyword_hits = sum(1 for kw in EXCITEMENT_KEYWORDS if kw in text_lower)
        commentary_bonus = min(keyword_hits * 0.04, 0.15)
        
        # Exclamation boost
        if "!" in commentary_text:
            commentary_bonus += 0.05

    total = min(base_score + replay_bonus + commentary_bonus, 1.0)
    return round(total, 3)
