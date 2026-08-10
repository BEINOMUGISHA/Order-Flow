from typing import Optional, Dict, List
import uuid
from ..schemas.models import Tick, AlertPayload, FootprintBar
from ..state.order_book import OrderBook


class IcebergEngine:
    """
    Probabilistic Iceberg / Hidden Order Detection Engine.
    Tracks accumulated trade executions at a price level relative to initial
    visible limit order depth.
    Outputs explicit confidence score (0.0 to 1.0) and failure mode metadata.
    """

    def __init__(self, fill_multiplier_threshold: float = 2.5):
        self.fill_multiplier_threshold = fill_multiplier_threshold
        # Tracks price -> {accumulated_fill: float, initial_visible_depth: float, fill_count: int, last_time: int}
        self.level_trackers: Dict[float, Dict[str, float]] = {}

    def check_iceberg(
        self,
        tick: Tick,
        order_book: OrderBook,
        active_bar: FootprintBar,
    ) -> Optional[AlertPayload]:
        price = tick.price
        side = tick.aggressor_side  # BUY aggressor fills Ask limit, SELL aggressor fills Bid limit
        book_side = "ASK" if side == "BUY" else "BID"
        current_visible = order_book.get_level_qty(book_side, price)

        if price not in self.level_trackers:
            self.level_trackers[price] = {
                "accumulated_fill": tick.quantity,
                "initial_visible_depth": max(current_visible, 0.001),
                "fill_count": 1,
                "last_time": tick.exchange_time,
            }
            return None

        tracker = self.level_trackers[price]

        # Reset tracker if timeout (> 10s between fills at level)
        if tick.exchange_time - tracker["last_time"] > 10000:
            tracker["accumulated_fill"] = tick.quantity
            tracker["initial_visible_depth"] = max(current_visible, 0.001)
            tracker["fill_count"] = 1
            tracker["last_time"] = tick.exchange_time
            return None

        tracker["accumulated_fill"] += tick.quantity
        tracker["fill_count"] += 1
        tracker["last_time"] = tick.exchange_time

        accumulated = tracker["accumulated_fill"]
        initial_depth = tracker["initial_visible_depth"]
        ratio = accumulated / initial_depth

        if ratio >= self.fill_multiplier_threshold and tracker["fill_count"] >= 3:
            # Calculate probabilistic confidence score
            # Higher ratio + higher fill count = higher confidence
            confidence = min(
                0.95,
                0.40 + (ratio / (self.fill_multiplier_threshold * 3)) * 0.40 + (tracker["fill_count"] / 20) * 0.15,
            )

            tier = "HIGH" if confidence >= 0.8 else ("MEDIUM" if confidence >= 0.6 else "LOW")

            failure_modes = [
                "Cannot distinguish genuine hidden order from independent traders coincidentally placing orders at same price",
                "High latency in L2 WebSocket feed might miscalculate visible resting depth",
            ]

            return AlertPayload(
                alert_id=f"ice_{uuid.uuid4().hex[:8]}",
                alert_type="ICEBERG_DETECTED",
                timestamp=tick.exchange_time,
                symbol=tick.symbol,
                price=tick.price,
                raw_metrics={
                    "accumulated_traded_volume": round(accumulated, 4),
                    "initial_visible_depth": round(initial_depth, 4),
                    "current_visible_depth": round(current_visible, 4),
                    "execution_count": int(tracker["fill_count"]),
                    "fill_ratio": round(ratio, 2),
                    "aggressor_side": side,
                },
                threshold_used={
                    "fill_multiplier_threshold": self.fill_multiplier_threshold,
                    "min_fill_count": 3,
                },
                confidence_score=round(confidence, 2),
                confidence_tier=tier,
                failure_modes=failure_modes,
                is_debounced=False,
            )

        return None
