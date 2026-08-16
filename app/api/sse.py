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
        print(f"[SSEManager] [CONNECT] SSE Client connected. Active listeners: {len(self._clients)}")
        return queue

    def disconnect(self, queue: asyncio.Queue):
        """Remove a disconnected listener queue."""
        if queue in self._clients:
            self._clients.discard(queue)
            print(f"[SSEManager] [DISCONNECT] SSE Client disconnected. Active listeners: {len(self._clients)}")

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
        if dead_queues:
            print(f"[SSEManager] [WARNING] Cleaned up {len(dead_queues)} dead/disconnected SSE queue(s). Active listeners: {len(self._clients)}")
