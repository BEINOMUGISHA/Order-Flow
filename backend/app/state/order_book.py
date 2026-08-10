from typing import Dict, List, Tuple, Optional
import time
from ..schemas.models import BookUpdate, OrderBookSnapshot, HealthStatus


class OrderBook:
    """
    In-memory limit order book with price level sorting, L2 differential updates,
    sequence gap detection, and REST snapshot resynchronization.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: Dict[float, float] = {}  # price -> qty
        self.asks: Dict[float, float] = {}  # price -> qty
        self.last_update_id: Optional[int] = None
        self.status: HealthStatus = HealthStatus()
        self.buffer: List[BookUpdate] = []
        self.is_resyncing: bool = False

    def get_snapshot(self) -> Dict[str, List[Tuple[float, float]]]:
        """Returns sorted top bids (desc) and asks (asc)."""
        sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
        sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])
        return {
            "bids": sorted_bids,
            "asks": sorted_asks,
        }

    def get_best_bid_ask(self) -> Tuple[Optional[float], Optional[float]]:
        best_bid = max(self.bids.keys()) if self.bids else None
        best_ask = min(self.asks.keys()) if self.asks else None
        return best_bid, best_ask

    def get_level_qty(self, side: str, price: float) -> float:
        """Returns visible resting quantity at price level."""
        if side.upper() == "BID":
            return self.bids.get(price, 0.0)
        else:
            return self.asks.get(price, 0.0)

    def apply_snapshot(self, snapshot: OrderBookSnapshot):
        """Applies fresh REST L2 order book snapshot."""
        self.bids = {p: q for p, q in snapshot.bids if q > 0}
        self.asks = {p: q for p, q in snapshot.asks if q > 0}
        self.last_update_id = snapshot.last_update_id

        # Process buffered updates
        applied_count = 0
        for update in self.buffer:
            if update.final_update_id <= snapshot.last_update_id:
                continue
            if update.first_update_id <= snapshot.last_update_id + 1 and update.final_update_id >= snapshot.last_update_id + 1:
                self._apply_update_raw(update)
                applied_count += 1
            elif self.last_update_id is not None and update.first_update_id == self.last_update_id + 1:
                self._apply_update_raw(update)
                applied_count += 1

        self.buffer.clear()
        self.is_resyncing = False
        self.status.state = "OK"
        self.status.last_sequence_id = self.last_update_id
        self.status.last_resync_timestamp = int(time.time() * 1000)
        self.status.message = f"Order book resynced at update ID {self.last_update_id}"

    def process_update(self, update: BookUpdate) -> bool:
        """
        Processes an incoming differential depth update.
        Returns True if update processed smoothly, False if sequence gap detected.
        """
        if self.is_resyncing:
            self.buffer.append(update)
            return True

        if self.last_update_id is None:
            # Not initialized yet, buffer and trigger resync
            self.is_resyncing = True
            self.buffer.append(update)
            self.status.state = "RESYNCING"
            self.status.message = "Initial state loading, snapshot needed"
            return False

        # Sequence gap validation
        # For Binance Futures: update.pu_final_update_id must match self.last_update_id
        # Or update.first_update_id == self.last_update_id + 1
        has_gap = False
        if update.pu_final_update_id is not None:
            if update.pu_final_update_id != self.last_update_id:
                has_gap = True
        elif update.first_update_id > self.last_update_id + 1:
            has_gap = True

        if has_gap:
            self.status.state = "DATA_GAP_DETECTED"
            self.status.gap_count += 1
            self.status.message = (
                f"Sequence Gap! Expected {self.last_update_id + 1}, got {update.first_update_id}"
            )
            self.is_resyncing = True
            self.buffer.append(update)
            return False

        self._apply_update_raw(update)
        return True

    def _apply_update_raw(self, update: BookUpdate):
        """Applies price level changes directly."""
        for p, q in update.bids:
            if q == 0:
                self.bids.pop(p, None)
            else:
                self.bids[p] = q

        for p, q in update.asks:
            if q == 0:
                self.asks.pop(p, None)
            else:
                self.asks[p] = q

        self.last_update_id = update.final_update_id
        self.status.last_sequence_id = self.last_update_id
