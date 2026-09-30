import json
import os
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MarketConfig(BaseModel):
    symbol: str
    provider: str = "simulated"
    asset_class: str = "other"
    tick_size: float = Field(gt=0)
    initial_price: float = Field(default=100.0, gt=0)
    bar_interval_ms: int = Field(default=60000, gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be empty")
        return normalized

    @field_validator("provider", "asset_class")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


def load_market_configs(raw: Optional[str] = None) -> List[MarketConfig]:
    """Load JSON market definitions from ORDERFLOW_MARKETS."""
    market_json = raw if raw is not None else os.getenv("ORDERFLOW_MARKETS")
    if not market_json:
        return [
            MarketConfig(
                symbol="BTCUSDT",
                provider="simulated",
                asset_class="crypto",
                tick_size=0.1,
                initial_price=65000.0,
            )
        ]

    definitions = json.loads(market_json)
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("ORDERFLOW_MARKETS must be a non-empty JSON array")

    markets = [MarketConfig.model_validate(item) for item in definitions]
    symbols = [market.symbol for market in markets]
    if len(symbols) != len(set(symbols)):
        raise ValueError("ORDERFLOW_MARKETS contains duplicate symbols")
    return markets