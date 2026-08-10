import pytest
import time
from backend.app.schemas.models import Tick
from backend.app.analytics.delta_engine import DeltaEngine
from backend.app.backtest.replay_engine import ReplayEngine


def test_delta_cvd_exact_reconciliation():
    """
    Enforces non-negotiable requirement:
    Delta bars must sum to CVD exactly (zero tolerance for drift).
    """
    engine = DeltaEngine(symbol="BTCUSDT", bar_interval_ms=60000, tick_size=0.1)
    base_time = 1700000000000

    ticks = [
        # Bar 1 (0ms to 59999ms)
        Tick(symbol="BTCUSDT", price=50000.0, quantity=1.5, trade_id="1", aggressor_side="BUY", exchange_time=base_time + 1000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),
        Tick(symbol="BTCUSDT", price=50001.0, quantity=2.0, trade_id="2", aggressor_side="SELL", exchange_time=base_time + 2000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),
        Tick(symbol="BTCUSDT", price=50000.5, quantity=3.0, trade_id="3", aggressor_side="BUY", exchange_time=base_time + 3000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),

        # Bar 2 (60000ms to 119999ms)
        Tick(symbol="BTCUSDT", price=50002.0, quantity=0.5, trade_id="4", aggressor_side="SELL", exchange_time=base_time + 61000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),
        Tick(symbol="BTCUSDT", price=50003.0, quantity=4.0, trade_id="5", aggressor_side="BUY", exchange_time=base_time + 62000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),

        # Bar 3 (120000ms to 179999ms)
        Tick(symbol="BTCUSDT", price=50001.0, quantity=1.0, trade_id="6", aggressor_side="SELL", exchange_time=base_time + 121000, local_receipt_time=time.time(), classification_method="EXCHANGE_FLAG"),
    ]

    completed_bars = []
    for t in ticks:
        cb, active = engine.process_tick(t)
        if cb:
            completed_bars.append(cb)

    # Sum of completed bar deltas + active bar delta
    sum_deltas = sum(b.delta for b in completed_bars) + (engine.current_bar.delta if engine.current_bar else 0.0)
    current_cvd = engine.current_bar.cvd if engine.current_bar else engine.session_cvd

    assert abs(sum_deltas - current_cvd) < 1e-9, f"Drift detected! Sum deltas: {sum_deltas}, CVD: {current_cvd}"


def test_replay_engine_reconciliation():
    replay = ReplayEngine(symbol="BTCUSDT", tick_size=0.1)
    base_time = 1700000000000

    ticks = []
    for i in range(100):
        side = "BUY" if i % 2 == 0 else "SELL"
        qty = 0.1 * (i + 1)
        ticks.append(
            Tick(
                symbol="BTCUSDT",
                price=50000.0 + (i * 0.1),
                quantity=qty,
                trade_id=str(i),
                aggressor_side=side,
                exchange_time=base_time + (i * 5000),
                local_receipt_time=time.time(),
                classification_method="EXCHANGE_FLAG",
            )
        )

    res = replay.replay_tick_sequence(ticks)
    assert res["reconciliation_passed"] is True
    assert res["ticks_processed"] == 100
