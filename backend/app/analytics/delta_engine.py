from typing import Dict, List, Optional, Tuple
import math
from ..schemas.models import Tick, FootprintBar, FootprintLevel


class DeltaEngine:
    """
    Footprint bar aggregator and Session Cumulative Volume Delta (CVD) calculator.
    Guarantees strict reconciliation between bar deltas and session CVD.
    """

    def __init__(
        self,
        symbol: str,
        bar_interval_ms: int = 60000,  # default 1-minute bars
        tick_size: float = 0.1,  # price bin size for level grouping
    ):
        self.symbol = symbol
        self.bar_interval_ms = bar_interval_ms
        self.tick_size = tick_size

        self.current_bar: Optional[FootprintBar] = None
        self.session_cvd: float = 0.0
        self.completed_bars: List[FootprintBar] = []

    def _round_price(self, price: float) -> float:
        """Rounds price to nearest tick size level."""
        return round(round(price / self.tick_size) * self.tick_size, 6)

    def process_tick(self, tick: Tick) -> Tuple[Optional[FootprintBar], FootprintBar]:
        """
        Processes a single incoming tick into the current footprint bar.
        Returns (completed_bar_if_any, active_current_bar).
        """
        rounded_price = self._round_price(tick.price)
        str_price = f"{rounded_price:.6f}".rstrip("0").rstrip(".")

        # Bar initialization or rollover
        completed_bar = None
        if (
            self.current_bar is None
            or tick.exchange_time >= self.current_bar.end_time
        ):
            if self.current_bar is not None:
                completed_bar = self._finalize_bar(self.current_bar)
                self.completed_bars.append(completed_bar)

            # Start new bar
            bar_start = (
                tick.exchange_time // self.bar_interval_ms
            ) * self.bar_interval_ms
            bar_end = bar_start + self.bar_interval_ms
            bar_id = f"{self.symbol}_{bar_start}"

            self.current_bar = FootprintBar(
                bar_id=bar_id,
                start_time=bar_start,
                end_time=bar_end,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                total_volume=0.0,
                buy_volume=0.0,
                sell_volume=0.0,
                delta=0.0,
                cvd=self.session_cvd,
                levels={},
            )

        # Update OHLC
        self.current_bar.high = max(self.current_bar.high, tick.price)
        self.current_bar.low = min(self.current_bar.low, tick.price)
        self.current_bar.close = tick.price

        # Update Footprint level
        if str_price not in self.current_bar.levels:
            self.current_bar.levels[str_price] = FootprintLevel(
                price=rounded_price,
                bid_vol=0.0,
                ask_vol=0.0,
                total_vol=0.0,
                delta=0.0,
            )

        level = self.current_bar.levels[str_price]
        if tick.aggressor_side == "BUY":
            level.ask_vol += tick.quantity
            self.current_bar.buy_volume += tick.quantity
        else:
            level.bid_vol += tick.quantity
            self.current_bar.sell_volume += tick.quantity

        level.total_vol += tick.quantity
        level.delta = level.ask_vol - level.bid_vol

        # Update bar metrics
        self.current_bar.total_volume += tick.quantity
        self.current_bar.delta = (
            self.current_bar.buy_volume - self.current_bar.sell_volume
        )
        self.current_bar.cvd = self.session_cvd + self.current_bar.delta

        # Update Point of Control (POC)
        max_vol = -1.0
        poc_p = self.current_bar.open
        for lvl_str, lvl in self.current_bar.levels.items():
            if lvl.total_vol > max_vol:
                max_vol = lvl.total_vol
                poc_p = lvl.price
        self.current_bar.poc_price = poc_p

        return completed_bar, self.current_bar

    def _finalize_bar(self, bar: FootprintBar) -> FootprintBar:
        """Finalizes bar statistics and updates session CVD."""
        self.session_cvd += bar.delta
        bar.cvd = self.session_cvd
        return bar

    def reset_session(self):
        """Resets session CVD for new trading session."""
        self.session_cvd = 0.0
        self.completed_bars.clear()
        self.current_bar = None
