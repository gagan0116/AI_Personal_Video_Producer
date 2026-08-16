import asyncio
import time
from typing import Callable, Awaitable, Optional


class MatchClock:
    """
    Simulates real-time match progression in accelerated time slices.
    
    Example at speed_multiplier=6.0:
    - 5 game-minutes (300,000 ms) is processed every 50 seconds.
    Example at speed_multiplier=20.0 (Fast demo mode):
    - 5 game-minutes (300,000 ms) is processed every 15 seconds.
    """

    def __init__(
        self,
        window_size_ms: int = 300_000,
        speed_multiplier: float = 6.0,
        on_window: Optional[Callable[[int, int, int], Awaitable[None]]] = None,
        on_tick: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
    ):
        self.window_size_ms = window_size_ms
        self.speed_multiplier = max(0.5, speed_multiplier)
        self.on_window = on_window
        self.on_tick = on_tick

        self.is_running = False
        self.is_paused = False
        self.current_half = 1
        self.current_position_ms = 0
        self._stop_requested = False

    def set_speed(self, multiplier: float):
        """Update speed multiplier dynamically."""
        self.speed_multiplier = max(0.5, multiplier)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
        self.is_paused = False
        self._stop_requested = True

    def get_display_time(self) -> str:
        total_seconds = self.current_position_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{self.current_half} - {minutes:02d}:{seconds:02d}"

    def get_progress_pct(self, half_duration_ms: int = 2_700_000) -> float:
        total_match_ms = half_duration_ms * 2
        current_total = (self.current_half - 1) * half_duration_ms + self.current_position_ms
        return min(round((current_total / total_match_ms) * 100.0, 1), 100.0)

    async def run_half(self, half: int, duration_ms: int = 2_700_000):
        """
        Execute windowed simulation for one half of the match.
        """
        self.current_half = half
        self.current_position_ms = 0
        self.is_running = True
        self._stop_requested = False

        while self.is_running and not self._stop_requested and self.current_position_ms < duration_ms:
            while self.is_paused and not self._stop_requested:
                await asyncio.sleep(0.2)

            if self._stop_requested:
                break

            window_start = self.current_position_ms
            window_end = min(window_start + self.window_size_ms, duration_ms)

            # Trigger window processing callback
            if self.on_window:
                await self.on_window(half, window_start, window_end)

            self.current_position_ms = window_end

            if self.on_tick:
                await self.on_tick(half, self.current_position_ms, self.get_display_time())

            # Real-world sleep duration adjusted by speed multiplier
            real_wait_sec = (self.window_size_ms / 1000.0) / self.speed_multiplier
            
            # Sleep in small slices to allow rapid pause/stop responsiveness
            steps = int(max(1, real_wait_sec / 0.1))
            step_duration = real_wait_sec / steps
            for _ in range(steps):
                if self._stop_requested or not self.is_running:
                    break
                while self.is_paused and not self._stop_requested:
                    await asyncio.sleep(0.2)
                await asyncio.sleep(step_duration)

        self.is_running = False
