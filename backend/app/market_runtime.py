import random
from typing import Any, Dict, List

from app.alerts.alert_manager import AlertManager
from app.analytics.absorption_engine import AbsorptionEngine
from app.analytics.delta_engine import DeltaEngine
from app.analytics.iceberg_engine import IcebergEngine
from app.analytics.imbalance_engine import ImbalanceEngine
from app.analytics.tape_speed_engine import TapeSpeedEngine
from app.ingestion.adapters import MarketEvent
from app.ingestion.market_config import MarketConfig
from app.schemas.models import BookUpdate, FootprintBar, OrderBookSnapshot, Tick
from app.state.order_book import OrderBook
from app.state.tape_buffer import RollingTapeBuffer


class MarketRuntime:
    def __init__(self, market: MarketConfig):
        self.market = market
        self.order_book = OrderBook(market.symbol)
        self.tape_buffer = RollingTapeBuffer()
        self.delta_engine = DeltaEngine(
            symbol=market.symbol,
            bar_interval_ms=market.bar_interval_ms,
            tick_size=market.tick_size,
        )
        self.absorption_engine = AbsorptionEngine(tick_size=market.tick_size)
        self.iceberg_engine = IcebergEngine()
        self.imbalance_engine = ImbalanceEngine()
        self.tape_speed_engine = TapeSpeedEngine()
        self.alert_manager = AlertManager()
        if market.provider == "simulated":
            self._seed_order_book()

    def _seed_order_book(self) -> None:
        center = self.market.initial_price
        tick = self.market.tick_size
        self.order_book.apply_snapshot(
            OrderBookSnapshot(
                symbol=self.market.symbol,
                last_update_id=0,
                bids=[(round(center - i * tick, 8), round(random.uniform(0.5, 5.0), 2)) for i in range(1, 11)],
                asks=[(round(center + i * tick, 8), round(random.uniform(0.5, 5.0), 2)) for i in range(1, 11)],
            )
        )

    def initial_state(self, available_markets: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "type": "INITIAL_STATE",
            "symbol": self.market.symbol,
            "markets": available_markets,
            "health": self.order_book.status.model_dump(),
            "completed_bars": [bar.model_dump() for bar in self.delta_engine.completed_bars[-20:]],
            "active_bar": self.delta_engine.current_bar.model_dump() if self.delta_engine.current_bar else None,
            "session_cvd": self.delta_engine.session_cvd,
            "alerts": [alert.model_dump() for alert in self.alert_manager.get_audit_log(20)],
        }

    def process_event(self, event: MarketEvent) -> Dict[str, Any]:
        if isinstance(event, OrderBookSnapshot):
            self.order_book.apply_snapshot(event)
            return {"type": "HEALTH_UPDATE", "health": self.order_book.status.model_dump()}
        if isinstance(event, BookUpdate):
            self.order_book.process_update(event)
            return {"type": "HEALTH_UPDATE", "health": self.order_book.status.model_dump()}
        if not isinstance(event, Tick):
            raise TypeError(f"Unsupported market event: {type(event).__name__}")
        if event.symbol != self.market.symbol:
            raise ValueError(f"Received {event.symbol} tick in {self.market.symbol} runtime")

        self.tape_buffer.add_tick(event)
        completed_bar, active_bar = self.delta_engine.process_tick(event)
        alerts = []
        candidates = [
            self.absorption_engine.check_absorption(event, self.tape_buffer, active_bar),
            self.iceberg_engine.check_iceberg(event, self.order_book, active_bar),
            self.tape_speed_engine.check_tape_speed(event, self.tape_buffer),
        ]
        if completed_bar:
            candidates.extend(self.imbalance_engine.evaluate_bar_imbalances(completed_bar))
        for candidate in candidates:
            if candidate:
                accepted = self.alert_manager.process_alert(candidate)
                if accepted:
                    alerts.append(accepted)

        return {
            "type": "TICK_UPDATE",
            "symbol": self.market.symbol,
            "tick": event.model_dump(),
            "active_bar": active_bar.model_dump(),
            "completed_bar": completed_bar.model_dump() if completed_bar else None,
            "session_cvd": active_bar.cvd,
            "health": self.order_book.status.model_dump(),
            "alerts": [alert.model_dump() for alert in alerts],
        }

    def completed_bars(self) -> List[FootprintBar]:
        return self.delta_engine.completed_bars

    def alerts(self, limit: int) -> list:
        return self.alert_manager.get_audit_log(limit=limit)