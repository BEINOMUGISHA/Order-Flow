import pytest
import time
from backend.app.schemas.models import Tick, FootprintBar, FootprintLevel, OrderBookSnapshot
from backend.app.state.order_book import OrderBook
from backend.app.state.tape_buffer import RollingTapeBuffer
from backend.app.analytics.absorption_engine import AbsorptionEngine
from backend.app.analytics.iceberg_engine import IcebergEngine


def test_iceberg_probabilistic_confidence():
    ob = OrderBook("BTCUSDT")
    ob.apply_snapshot(
        OrderBookSnapshot(
            symbol="BTCUSDT",
            last_update_id=100,
            bids=[(50000.0, 1.0)],  # Visible depth 1.0 BTC
            asks=[(50001.0, 1.0)],
        )
    )

    ice_engine = IcebergEngine(fill_multiplier_threshold=2.0)
    bar = FootprintBar(
        bar_id="bar1", start_time=1000, end_time=60000, open=50000.0, high=50000.0, low=50000.0, close=50000.0
    )

    # 4 repeated sell fills at 50000.0 total 3.0 BTC (exceeding visible 1.0 BTC)
    alert = None
    for i in range(4):
        tick = Tick(
            symbol="BTCUSDT",
            price=50000.0,
            quantity=0.75,
            trade_id=str(i),
            aggressor_side="SELL",  # Fills bid
            exchange_time=1000 + (i * 500),
            local_receipt_time=time.time(),
            classification_method="EXCHANGE_FLAG",
        )
        res = ice_engine.check_iceberg(tick, ob, bar)
        if res:
            alert = res

    assert alert is not None
    assert alert.alert_type == "ICEBERG_DETECTED"
    assert alert.confidence_score > 0.0
    assert alert.confidence_tier in ["HIGH", "MEDIUM", "LOW"]
    assert len(alert.failure_modes) > 0  # Cites known failure modes explicitly


def test_absorption_statistical_outlier():
    tape = RollingTapeBuffer(max_size=100)
    # Populate tape with baseline normal trade size ~1.0 BTC
    for i in range(20):
        qty = 0.9 + (i % 3) * 0.1  # 0.9, 1.0, 1.1
        tape.add_tick(
            Tick(
                symbol="BTCUSDT",
                price=50000.0,
                quantity=qty,
                trade_id=str(i),
                aggressor_side="BUY",
                exchange_time=1000 + (i * 100),
                local_receipt_time=time.time(),
                classification_method="EXCHANGE_FLAG",
            )
        )

    abs_engine = AbsorptionEngine(std_dev_threshold=2.0, max_tick_movement=2, tick_size=0.1)
    bar = FootprintBar(
        bar_id="bar1", start_time=1000, end_time=60000, open=50000.0, high=50000.1, low=49999.9, close=50000.0
    )

    # Outlier trade: 10.0 BTC (way above mean 1.0)
    outlier_tick = Tick(
        symbol="BTCUSDT",
        price=50000.0,
        quantity=10.0,
        trade_id="outlier",
        aggressor_side="BUY",
        exchange_time=5000,
        local_receipt_time=time.time(),
        classification_method="EXCHANGE_FLAG",
    )

    alert = abs_engine.check_absorption(outlier_tick, tape, bar)
    assert alert is not None
    assert alert.alert_type == "ABSORPTION_EVENT"
    assert alert.raw_metrics["trade_quantity"] == 10.0
