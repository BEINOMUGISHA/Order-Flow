import pytest

from app.ingestion.market_config import MarketConfig, load_market_configs


def test_loads_multiple_normalized_markets():
    markets = load_market_configs(
        '[{"symbol":" btcusdt ","provider":"SIMULATED","asset_class":"Crypto",'
        '"tick_size":0.1,"initial_price":65000},'
        '{"symbol":"AAPL","provider":"alpaca","asset_class":"equity",'
        '"tick_size":0.01,"initial_price":200}]'
    )

    assert [market.symbol for market in markets] == ["BTCUSDT", "AAPL"]
    assert markets[1].provider == "alpaca"
    assert markets[1].asset_class == "equity"


def test_rejects_duplicate_symbols():
    with pytest.raises(ValueError, match="duplicate symbols"):
        load_market_configs(
            '[{"symbol":"aapl","tick_size":0.01},'
            '{"symbol":"AAPL","tick_size":0.01}]'
        )


def test_requires_positive_tick_size():
    with pytest.raises(ValueError):
        MarketConfig(symbol="AAPL", tick_size=0)