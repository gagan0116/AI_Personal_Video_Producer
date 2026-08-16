from typing import List, Dict, Any


class MockVSSClient:
    """
    Mock VSS Client simulating NVIDIA VSS skills responses
    for local development, CI testing, and graceful offline fallback.
    """

    def __init__(self, base_url: str = "mock://vss"):
        self.base_url = base_url

    async def check_health(self) -> bool:
        return True

    async def ingest_video(self, video_path: str, stream_id: str) -> Dict[str, Any]:
        return {"stream_id": stream_id, "status": "mock_ingested", "uri": video_path}

    async def get_dense_captions(
        self, stream_id: str, start_ms: int, end_ms: int
    ) -> List[Dict[str, Any]]:
        # Generates realistic synthetic Cosmos Reason VLM dense captions
        captions = []
        midpoint = (start_ms + end_ms) // 2
        captions.append({
            "timestamp_ms": midpoint,
            "description": "Tactical high-angle broadcast view. Attackers in home kit pressing forward into final third, opposing backline stepping up to hold defensive line.",
            "confidence": 0.94
        })
        return captions

    async def ask_video(
        self, stream_id: str, timestamp_ms: int, question: str
    ) -> str:
        q_lower = question.lower()
        if "neymar" in q_lower or "player" in q_lower:
            return "Player in number 11 kit is actively dribbling past defenders along the left touchline, cutting inside towards the penalty box."
        elif "defensive" in q_lower or "tactical" in q_lower:
            return "Defensive line is caught stepping forward; spacing between center-backs has widened, creating an open passing lane through the channel."
        elif "goal" in q_lower or "celebration" in q_lower:
            return "Ball crosses the goal line into the top right corner. Striker sprints towards the corner flag with teammates jumping in celebration as crowd erupts."
        return "Camera shows wide stadium view with active play near midfield."

    async def search_archive(
        self, stream_id: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp_ms": 195000,
                "score": 0.92,
                "snippet": "High excitement moment with ball entering net and crowd reaction."
            }
        ]

    async def close(self):
        pass
