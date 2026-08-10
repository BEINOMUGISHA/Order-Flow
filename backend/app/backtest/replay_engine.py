from typing import List, Dict, Any, Tuple, Optional
from ..schemas.models import Tick, BookUpdate, FootprintBar, AlertPayload
from ..state.order_book import OrderBook
from ..state.tape_buffer import RollingTapeBuffer
from ..analytics.delta_engine import DeltaEngine
from ..analytics.absorption_engine import AbsorptionEngine
from ..analytics.iceberg_engine import IcebergEngine
from ..analytics.imbalance_engine import ImbalanceEngine
from ..analytics.tape_speed_engine import TapeSpeedEngine
from ..alerts.alert_manager import AlertManager


class ReplayEngine:
    """
    Validation and Backtesting Harness:
    Replays historical tick data through the EXACT same live analytics code path.
    Enforces delta & CVD reconciliation and produces signal performance reports.
    """

    def __init__(self, symbol: str = "BTCUSDT", tick_size: float = 0.1):
        self.symbol = symbol
        self.order_book = OrderBook(symbol)
        self.tape_buffer = RollingTapeBuffer()
        self.delta_engine = DeltaEngine(symbol=symbol, tick_size=tick_size)
        self.absorption_engine = AbsorptionEngine(tick_size=tick_size)
        self.iceberg_engine = IcebergEngine()
        self.imbalance_engine = ImbalanceEngine()
        self.tape_speed_engine = TapeSpeedEngine()
        self.alert_manager = AlertManager()

    def process_tick(self, tick: Tick) -> Tuple[Optional[FootprintBar], FootprintBar, List[AlertPayload]]:
        """Executes a single tick through live engine logic."""
        self.tape_buffer.add_tick(tick)
        completed_bar, active_bar = self.delta_engine.process_tick(tick)

        generated_alerts = []

        # Check absorption
        abs_alert = self.absorption_engine.check_absorption(tick, self.tape_buffer, active_bar)
        if abs_alert:
            processed = self.alert_manager.process_alert(abs_alert)
            if processed:
                generated_alerts.append(processed)

        # Check iceberg
        ice_alert = self.iceberg_engine.check_iceberg(tick, self.order_book, active_bar)
        if ice_alert:
            processed = self.alert_manager.process_alert(ice_alert)
            if processed:
                generated_alerts.append(processed)

        # Check tape speed
        tsp_alert = self.tape_speed_engine.check_tape_speed(tick, self.tape_buffer)
        if tsp_alert:
            processed = self.alert_manager.process_alert(tsp_alert)
            if processed:
                generated_alerts.append(processed)

        # Check imbalances on completed bar
        if completed_bar:
            imb_alerts = self.imbalance_engine.evaluate_bar_imbalances(completed_bar)
            for imb in imb_alerts:
                processed = self.alert_manager.process_alert(imb)
                if processed:
                    generated_alerts.append(processed)

        return completed_bar, active_bar, generated_alerts

    def replay_tick_sequence(self, ticks: List[Tick]) -> Dict[str, Any]:
        """Replays list of ticks and validates reconciliation math."""
        all_completed_bars = []
        all_alerts = []

        for t in ticks:
            completed_bar, active_bar, alerts = self.process_tick(t)
            if completed_bar:
                all_completed_bars.append(completed_bar)
            all_alerts.extend(alerts)

        # Sanity check: sum of bar deltas == final session CVD
        sum_bar_deltas = sum(b.delta for b in all_completed_bars)
        if self.delta_engine.current_bar:
            sum_bar_deltas += self.delta_engine.current_bar.delta

        final_cvd = self.delta_engine.session_cvd
        if self.delta_engine.current_bar:
            final_cvd = self.delta_engine.current_bar.cvd

        reconciled = abs(sum_bar_deltas - final_cvd) < 1e-6

        return {
            "ticks_processed": len(ticks),
            "bars_completed": len(all_completed_bars),
            "alerts_generated": len(all_alerts),
            "sum_bar_deltas": sum_bar_deltas,
            "final_session_cvd": final_cvd,
            "reconciliation_passed": reconciled,
        }
