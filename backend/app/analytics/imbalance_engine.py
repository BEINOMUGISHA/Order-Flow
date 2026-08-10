from typing import Optional, List
import uuid
from ..schemas.models import FootprintBar, AlertPayload, Tick


class ImbalanceEngine:
    """
    Bid/Ask Imbalance Detector:
    Evaluates volume imbalances per price level using a configurable threshold ratio (default 3:1).
    """

    def __init__(self, ratio_threshold: float = 3.0, min_volume_threshold: float = 1.0):
        self.ratio_threshold = ratio_threshold
        self.min_volume_threshold = min_volume_threshold

    def evaluate_bar_imbalances(self, bar: FootprintBar) -> List[AlertPayload]:
        alerts = []
        for str_p, level in bar.levels.items():
            ask = level.ask_vol
            bid = level.bid_vol

            # Check Buy Imbalance (Ask / Bid >= threshold)
            if ask >= self.min_volume_threshold and (bid == 0 or ask / max(bid, 0.001) >= self.ratio_threshold):
                level.imbalance_flag = "BUY_IMBALANCE"
                ratio = ask / max(bid, 0.001)
                alerts.append(
                    AlertPayload(
                        alert_id=f"imb_{uuid.uuid4().hex[:8]}",
                        alert_type="IMBALANCE_BREACH",
                        timestamp=bar.end_time,
                        symbol=bar.bar_id.split("_")[0],
                        price=level.price,
                        raw_metrics={
                            "ask_vol": round(ask, 4),
                            "bid_vol": round(bid, 4),
                            "ratio": round(ratio, 2),
                            "direction": "BUY_IMBALANCE",
                        },
                        threshold_used={"ratio_threshold": self.ratio_threshold},
                        confidence_score=1.0,
                        confidence_tier="HIGH",
                        failure_modes=[],
                        is_debounced=False,
                    )
                )

            # Check Sell Imbalance (Bid / Ask >= threshold)
            elif bid >= self.min_volume_threshold and (ask == 0 or bid / max(ask, 0.001) >= self.ratio_threshold):
                level.imbalance_flag = "SELL_IMBALANCE"
                ratio = bid / max(ask, 0.001)
                alerts.append(
                    AlertPayload(
                        alert_id=f"imb_{uuid.uuid4().hex[:8]}",
                        alert_type="IMBALANCE_BREACH",
                        timestamp=bar.end_time,
                        symbol=bar.bar_id.split("_")[0],
                        price=level.price,
                        raw_metrics={
                            "ask_vol": round(ask, 4),
                            "bid_vol": round(bid, 4),
                            "ratio": round(ratio, 2),
                            "direction": "SELL_IMBALANCE",
                        },
                        threshold_used={"ratio_threshold": self.ratio_threshold},
                        confidence_score=1.0,
                        confidence_tier="HIGH",
                        failure_modes=[],
                        is_debounced=False,
                    )
                )
            else:
                level.imbalance_flag = "NONE"

        return alerts
