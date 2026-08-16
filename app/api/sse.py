import asyncio
import json
from typing import Set, Dict, Any


class SSEManager:
    """
    Server-Sent Events (SSE) Manager for streaming live match updates,
    agent outputs, and timeline events to the frontend dashboard.
    """

    def __init__(self):
        self._clients: Set[asyncio.Queue] = set()

    def connect(self) -> asyncio.Queue:
        """Register a new browser listener queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._clients.add(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue):
        """Remove a disconnected listener queue."""
        self._clients.discard(queue)

    async def emit(self, event_type: str, data: Any):
        """
        Broadcast an SSE message to all connected browsers.
        """
        if not self._clients:
            return

        serialized = json.dumps(data) if not isinstance(data, str) else data
        message = {
            "event": event_type,
            "data": serialized
        }

        dead_queues = []
        for queue in list(self._clients):
            try:
                # If queue is full, drop oldest or push directly
                if queue.full():
                    try:
                        queue.get_nowait()
                    except Exception:
                        pass
                queue.put_nowait(message)
            except Exception:
                dead_queues.append(queue)

        for dead in dead_queues:
            self._clients.discard(dead)
