import pytest
from backend.app.ingestion.tick_classifier import LeeReadyTickClassifier


def test_exchange_flag_priority():
    classifier = LeeReadyTickClassifier()

    # Buyer Maker = True -> Seller Taker (SELL)
    side, method = classifier.classify_trade(price=50000.0, is_buyer_maker=True)
    assert side == "SELL"
    assert method == "EXCHANGE_FLAG"

    # Buyer Maker = False -> Buyer Taker (BUY)
    side, method = classifier.classify_trade(price=50000.0, is_buyer_maker=False)
    assert side == "BUY"
    assert method == "EXCHANGE_FLAG"


def test_lee_ready_tick_rule():
    classifier = LeeReadyTickClassifier()

    # Initial trade
    side, method = classifier.classify_trade(price=50000.0)
    assert side == "BUY"

    # Uptick -> BUY
    side, method = classifier.classify_trade(price=50001.0)
    assert side == "BUY"
    assert method == "LEE_READY_TICK_RULE"

    # Downtick -> SELL
    side, method = classifier.classify_trade(price=49999.0)
    assert side == "SELL"
    assert method == "LEE_READY_TICK_RULE"

    # Zero-tick -> repeat previous (SELL)
    side, method = classifier.classify_trade(price=49999.0)
    assert side == "SELL"
    assert method == "LEE_READY_TICK_RULE"
