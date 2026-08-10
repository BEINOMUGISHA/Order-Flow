from typing import Optional, List
import uuid
from ..schemas.models import Tick, AlertPayload, FootprintBar
from ..state.tape_buffer import RollingTapeBuffer


class AbsorptionEngine:
    """
    Absorption Detection Engine:
    Detects large volume traded at a price level with minimal price movement.
    - Large volume = statistical outlier (> 2 std dev above rolling mean trade volume).
    - Minimal movement = price movement <= tick_threshold.
    """

    def __init__(
        self,
        std_dev_threshold: float = 2.0,
        max_tick_movement: int = 2,
        tick_size: float = 0.1,
    ):
        self.std_dev_threshold = std_dev_threshold
        self.max_tick_movement = max_tick_movement
        self.tick_size = tick_size

    def check_absorption(
        self,
        tick: Tick,
        tape_buffer: RollingTapeBuffer,
        active_bar: FootprintBar,
    ) -> Optional[AlertPayload]:
        mean_size, std_size = tape_buffer.get_trade_size_stats()

        if std_size <= 0:
            return None

        # Check statistical outlier condition
        outlier_size_cutoff = mean_size + (self.std_dev_threshold * std_size)
        if tick.quantity < outlier_size_cutoff:
            return None

        # Check price movement in recent trades (e.g. range in active bar or current price movement)
        price_range = active_bar.high - active_bar.low
        max_allowed_range = self.max_tick_movement * self.tick_size

        if price_range > max_allowed_range:
            return None

        # Confidence calculation
        # Higher volume relative to std dev -> higher confidence score
        z_score = (tick.quantity - mean_size) / std_size
        confidence = min(1.0, max(0.5, 0.5 + (z_score - 2.0) * 0.15))

        tier = "HIGH" if confidence >= 0.8 else ("MEDIUM" if confidence >= 0.6 else "LOW")

        failure_modes = []
        if active_bar.total_volume < mean_size * 5:
            failure_modes.append("Low overall bar sample size")

        return AlertPayload(
            alert_id=f"abs_{uuid.uuid4().hex[:8]}",
            alert_type="ABSORPTION_EVENT",
            timestamp=tick.exchange_time,
            symbol=tick.symbol,
            price=tick.price,
            raw_metrics={
                "trade_quantity": tick.quantity,
                "rolling_mean": round(mean_size, 4),
                "rolling_std": round(std_size, 4),
                "z_score": round(z_score, 2),
                "bar_price_range": round(price_range, 4),
                "aggressor_side": tick.aggressor_side,
            },
            threshold_used={
                "std_dev_threshold": self.std_dev_threshold,
                "max_tick_movement": self.max_tick_movement,
                "outlier_cutoff": round(outlier_size_cutoff, 4),
            },
            confidence_score=round(confidence, 2),
            confidence_tier=tier,
            failure_modes=failure_modes,
            is_debounced=False,
        )
