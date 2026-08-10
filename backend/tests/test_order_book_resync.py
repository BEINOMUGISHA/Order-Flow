import pytest
from backend.app.schemas.models import BookUpdate, OrderBookSnapshot
from backend.app.state.order_book import OrderBook


def test_order_book_sequence_gap_and_resync():
    ob = OrderBook("BTCUSDT")

    # Initial L2 snapshot
    snapshot = OrderBookSnapshot(
        symbol="BTCUSDT",
        last_update_id=100,
        bids=[(50000.0, 2.0), (49999.0, 5.0)],
        asks=[(50001.0, 1.5), (50002.0, 3.0)],
    )
    ob.apply_snapshot(snapshot)

    assert ob.status.state == "OK"
    assert ob.last_update_id == 100
    assert ob.get_level_qty("BID", 50000.0) == 2.0

    # Normal update (first_u=101, final_u=102)
    update1 = BookUpdate(
        symbol="BTCUSDT",
        first_update_id=101,
        final_update_id=102,
        pu_final_update_id=100,
        bids=[(50000.0, 3.5)],
        asks=[],
        exchange_time=1700000001000,
    )
    ok = ob.process_update(update1)
    assert ok is True
    assert ob.last_update_id == 102
    assert ob.get_level_qty("BID", 50000.0) == 3.5

    # Sequence Gap! (Expected 103, got 108)
    update_gap = BookUpdate(
        symbol="BTCUSDT",
        first_update_id=108,
        final_update_id=109,
        pu_final_update_id=107,
        bids=[(50000.0, 10.0)],
        asks=[],
        exchange_time=1700000005000,
    )
    ok = ob.process_update(update_gap)
    assert ok is False
    assert ob.status.state == "DATA_GAP_DETECTED"
    assert ob.status.gap_count == 1
    assert ob.is_resyncing is True

    # Fresh Snapshot received at update 110
    snapshot2 = OrderBookSnapshot(
        symbol="BTCUSDT",
        last_update_id=110,
        bids=[(50000.0, 4.0)],
        asks=[(50001.0, 2.0)],
    )
    ob.apply_snapshot(snapshot2)

    assert ob.status.state == "OK"
    assert ob.last_update_id == 110
    assert ob.get_level_qty("BID", 50000.0) == 4.0
