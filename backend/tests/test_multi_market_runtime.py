import time

import pytest

from app.ingestion.market_config import MarketConfig
from app.market_runtime import MarketRuntime
from app.schemas.models import Tick


def make_tick(symbol: str, price: float, exchange_time: int) -> Tick:
    return Tick(
        symbol=symbol,
        price=price,
        quantity=1.0,
        trade_id=f"{symbol}-{exchange_time}",
        aggressor_side="BUY",
        exchange_time=exchange_time,
        local_receipt_time=time.time(),
        classification_method="EXCHANGE_FLAG",
    )


def test_market_runtime_keeps_instrument_state_isolated():
    btc = MarketRuntime(
        MarketConfig(symbol="BTCUSDT", tick_size=0.1, initial_price=65000)
    )
    aapl = MarketRuntime(
        MarketConfig(symbol="AAPL", asset_class="equity", tick_size=0.01, initial_price=200)
    )

    btc.process_event(make_tick("BTCUSDT", 65000.1, 1_000_000))

    assert btc.delta_engine.current_bar is not None
    assert btc.delta_engine.current_bar.cvd == 1.0
    assert aapl.delta_engine.current_bar is None
    assert btc.delta_engine.tick_size == 0.1
    assert aapl.delta_engine.tick_size == 0.01


def test_market_runtime_rejects_cross_instrument_ticks():
    runtime = MarketRuntime(MarketConfig(symbol="AAPL", tick_size=0.01))

    with pytest.raises(ValueError, match="Received MSFT tick"):
        runtime.process_event(make_tick("MSFT", 200, 1_000_000))


def test_non_simulated_market_does_not_start_with_fabricated_depth():
    runtime = MarketRuntime(
        MarketConfig(
            symbol="AAPL",
            provider="alpaca",
            asset_class="equity",
            tick_size=0.01,
        )
    )

    assert runtime.order_book.bids == {}
    assert runtime.order_book.asks == {}