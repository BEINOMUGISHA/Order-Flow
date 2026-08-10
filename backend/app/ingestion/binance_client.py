import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional, Callable, Dict, Any
import httpx
import websockets
from ..schemas.models import Tick, BookUpdate, OrderBookSnapshot, HealthStatus
from .tick_classifier import LeeReadyTickClassifier

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Production-grade Binance WebSocket & REST Ingestion Client.
    Supports Spot & Futures WS depth and trade streams with automatic exponential backoff,
    sequence gap detection, and normalized Tick/BookUpdate parsing.
    """

    def __init__(self, symbol: str = "BTCUSDT", is_futures: bool = True):
        self.symbol = symbol.upper()
        self.is_futures = is_futures
        self.classifier = LeeReadyTickClassifier()
        self.status = HealthStatus()
        self.running = False

        if is_futures:
            self.ws_base_url = "wss://fstream.binance.com/ws"
            self.rest_base_url = "https://fapi.binance.com"
        else:
            self.ws_base_url = "wss://stream.binance.com:9443/ws"
            self.rest_base_url = "https://api.binance.com"

    async def fetch_l2_snapshot(self, limit: int = 1000) -> OrderBookSnapshot:
        """Fetches fresh REST L2 order book snapshot."""
        endpoint = "/fapi/v1/depth" if self.is_futures else "/api/v3/depth"
        url = f"{self.rest_base_url}{endpoint}?symbol={self.symbol}&limit={limit}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            bids = [(float(p), float(q)) for p, q in data["bids"]]
            asks = [(float(p), float(q)) for p, q in data["asks"]]
            last_id = data["lastUpdateId"]

            return OrderBookSnapshot(
                symbol=self.symbol,
                last_update_id=last_id,
                bids=bids,
                asks=asks,
            )

    def parse_trade_msg(self, data: Dict[str, Any]) -> Tick:
        """Parses WebSocket trade event (@trade or @aggTrade) into normalized Tick schema."""
        local_receipt = time.time()
        event_type = data.get("e", "trade")

        if event_type == "aggTrade":
            price = float(data["p"])
            qty = float(data["q"])
            trade_id = str(data["a"])
            exchange_time = int(data["T"])
            is_buyer_maker = bool(data["m"])
        else:
            price = float(data["p"])
            qty = float(data["q"])
            trade_id = str(data["t"])
            exchange_time = int(data["T"])
            is_buyer_maker = bool(data["m"])

        side, method = self.classifier.classify_trade(
            price=price,
            is_buyer_maker=is_buyer_maker,
        )

        return Tick(
            symbol=self.symbol,
            price=price,
            quantity=qty,
            trade_id=trade_id,
            aggressor_side=side,
            exchange_time=exchange_time,
            local_receipt_time=local_receipt,
            classification_method=method,
        )

    def parse_depth_msg(self, data: Dict[str, Any]) -> BookUpdate:
        """Parses WebSocket depth event (@depth@100ms) into normalized BookUpdate schema."""
        exchange_time = int(data.get("E", time.time() * 1000))
        first_u = int(data["U"])
        final_u = int(data["u"])
        pu = int(data["pu"]) if "pu" in data else None

        bids = [(float(p), float(q)) for p, q in data.get("b", [])]
        asks = [(float(p), float(q)) for p, q in data.get("a", [])]

        return BookUpdate(
            symbol=self.symbol,
            first_update_id=first_u,
            final_update_id=final_u,
            pu_final_update_id=pu,
            bids=bids,
            asks=asks,
            exchange_time=exchange_time,
        )
