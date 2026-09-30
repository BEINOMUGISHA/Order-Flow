import asyncio
import random
import time
from typing import AsyncIterator, Callable, Dict, Protocol, Union

from app.schemas.models import BookUpdate, OrderBookSnapshot, Tick
from app.ingestion.market_config import MarketConfig


MarketEvent = Union[Tick, BookUpdate, OrderBookSnapshot]


class MarketDataAdapter(Protocol):
    def stream(self, market: MarketConfig) -> AsyncIterator[MarketEvent]:
        """Yield normalized market events for one configured instrument."""


class SimulatedMarketDataAdapter:
    async def stream(self, market: MarketConfig) -> AsyncIterator[MarketEvent]:
        price = market.initial_price
        trade_id = 0
        while True:
            await asyncio.sleep(random.uniform(0.05, 0.2))
            price = max(market.tick_size, price + random.choice((-1, 0, 0, 1)) * market.tick_size)
            quantity = (
                random.uniform(8.0, 15.0)
                if random.random() < 0.05
                else random.uniform(0.01, 1.5)
            )
            trade_id += 1
            now_ms = int(time.time() * 1000)
            yield Tick(
                symbol=market.symbol,
                price=round(price, 8),
                quantity=round(quantity, 8),
                trade_id=str(trade_id),
                aggressor_side=random.choice(("BUY", "SELL")),
                exchange_time=now_ms,
                local_receipt_time=time.time(),
                classification_method="EXCHANGE_FLAG",
            )


AdapterFactory = Callable[[], MarketDataAdapter]
_adapter_factories: Dict[str, AdapterFactory] = {
    "simulated": SimulatedMarketDataAdapter,
}


def register_market_data_adapter(provider: str, factory: AdapterFactory) -> None:
    normalized_provider = provider.strip().lower()
    if not normalized_provider:
        raise ValueError("provider must not be empty")
    _adapter_factories[normalized_provider] = factory


def create_market_data_adapter(provider: str) -> MarketDataAdapter:
    normalized_provider = provider.strip().lower()
    try:
        return _adapter_factories[normalized_provider]()
    except KeyError as error:
        available = ", ".join(sorted(_adapter_factories))
        raise ValueError(
            f"No market-data adapter is registered for '{provider}'. Available: {available}"
        ) from error