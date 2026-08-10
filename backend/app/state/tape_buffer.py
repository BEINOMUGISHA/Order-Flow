from collections import deque
from typing import List, Tuple
import numpy as np
from ..schemas.models import Tick


class RollingTapeBuffer:
    """
    Rolling tape buffer maintaining recent execution ticks for rolling statistics,
    tape speed calculation, and baseline outlier detection.
    """

    def __init__(self, max_size: int = 10000, time_window_seconds: float = 300.0):
        self.max_size = max_size
        self.time_window_ms = int(time_window_seconds * 1000)
        self.ticks: deque[Tick] = deque(maxlen=max_size)

    def add_tick(self, tick: Tick):
        self.ticks.append(tick)
        self._prune_old_ticks(tick.exchange_time)

    def _prune_old_ticks(self, current_time_ms: int):
        cutoff = current_time_ms - self.time_window_ms
        while self.ticks and self.ticks[0].exchange_time < cutoff:
            self.ticks.popleft()

    def get_recent_ticks(self) -> List[Tick]:
        return list(self.ticks)

    def get_trade_size_stats(self) -> Tuple[float, float]:
        """
        Returns (mean_trade_size, std_trade_size) over rolling window.
        Returns (0.0, 0.0) if fewer than 2 ticks.
        """
        if len(self.ticks) < 2:
            return (self.ticks[0].quantity, 0.0) if self.ticks else (0.0, 0.0)

        sizes = [t.quantity for t in self.ticks]
        mean = float(np.mean(sizes))
        std = float(np.std(sizes))
        return mean, std

    def get_tape_speed(self, window_seconds: float = 10.0) -> Tuple[float, float]:
        """
        Returns (trades_per_sec, volume_per_sec) over recent window_seconds.
        """
        if not self.ticks:
            return 0.0, 0.0

        latest_time = self.ticks[-1].exchange_time
        cutoff = latest_time - int(window_seconds * 1000)

        count = 0
        volume = 0.0
        for t in reversed(self.ticks):
            if t.exchange_time < cutoff:
                break
            count += 1
            volume += t.quantity

        actual_duration = max(window_seconds, 1.0)
        return count / actual_duration, volume / actual_duration
