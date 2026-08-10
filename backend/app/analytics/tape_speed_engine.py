from typing import Optional
import uuid
from ..schemas.models import Tick, AlertPayload
from ..state.tape_buffer import RollingTapeBuffer


class TapeSpeedEngine:
    """
    Tape Speed Engine:
    Calculates trades/sec and volume/sec, detecting execution velocity spikes relative to rolling baseline.
    """

    def __init__(self, spike_multiplier_threshold: float = 2.5):
        self.spike_multiplier_threshold = spike_multiplier_threshold

    def check_tape_speed(
        self,
        tick: Tick,
        tape_buffer: RollingTapeBuffer,
    ) -> Optional[AlertPayload]:
        # Fast recent window (e.g. 5 seconds) vs baseline window (e.g. 60 seconds)
        fast_tps, fast_vps = tape_buffer.get_tape_speed(window_seconds=5.0)
        baseline_tps, baseline_vps = tape_buffer.get_tape_speed(window_seconds=60.0)

        if baseline_tps <= 0.5:
            return None  # Insufficient baseline data

        tps_ratio = fast_tps / baseline_tps

        if tps_ratio >= self.spike_multiplier_threshold:
            confidence = min(0.95, 0.5 + (tps_ratio / 10.0) * 0.45)
            tier = "HIGH" if confidence >= 0.8 else ("MEDIUM" if confidence >= 0.6 else "LOW")

            return AlertPayload(
                alert_id=f"tsp_{uuid.uuid4().hex[:8]}",
                alert_type="TAPE_SPEED_SPIKE",
                timestamp=tick.exchange_time,
                symbol=tick.symbol,
                price=tick.price,
                raw_metrics={
                    "recent_trades_per_sec": round(fast_tps, 2),
                    "baseline_trades_per_sec": round(baseline_tps, 2),
                    "recent_vol_per_sec": round(fast_vps, 4),
                    "baseline_vol_per_sec": round(baseline_vps, 4),
                    "speed_multiplier": round(tps_ratio, 2),
                },
                threshold_used={
                    "spike_multiplier_threshold": self.spike_multiplier_threshold,
                },
                confidence_score=round(confidence, 2),
                confidence_tier=tier,
                failure_modes=[],
                is_debounced=False,
            )

        return None
