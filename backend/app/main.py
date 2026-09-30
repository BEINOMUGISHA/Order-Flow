import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.ingestion.adapters import MarketDataAdapter, create_market_data_adapter
from app.ingestion.market_config import MarketConfig, load_market_configs
from app.market_runtime import MarketRuntime
from app.schemas.models import AlertPayload, FootprintBar, HealthStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrderFlowApp")

app = FastAPI(title="Real-Time Order Flow Engine API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

markets: List[MarketConfig] = load_market_configs()
market_runtimes = {market.symbol: MarketRuntime(market) for market in markets}
market_adapters: Dict[str, MarketDataAdapter] = {
    market.symbol: create_market_data_adapter(market.provider) for market in markets
}
default_symbol = markets[0].symbol
active_connections: Dict[WebSocket, str] = {}
feed_tasks: List[asyncio.Task] = []


class ConnectionManager:
    @staticmethod
    async def connect(websocket: WebSocket, symbol: str) -> None:
        await websocket.accept()
        active_connections[websocket] = symbol
        logger.info("WebSocket connected for %s (%s clients)", symbol, len(active_connections))

    @staticmethod
    def disconnect(websocket: WebSocket) -> None:
        active_connections.pop(websocket, None)

    @staticmethod
    async def broadcast(symbol: str, message: Dict[str, Any]) -> None:
        payload = json.dumps(message)
        disconnected = []
        for connection, subscribed_symbol in active_connections.items():
            if subscribed_symbol != symbol:
                continue
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            active_connections.pop(connection, None)


def get_runtime(symbol: Optional[str]) -> MarketRuntime:
    selected_symbol = (symbol or default_symbol).strip().upper()
    runtime = market_runtimes.get(selected_symbol)
    if runtime is None:
        raise HTTPException(status_code=404, detail=f"Unknown market: {selected_symbol}")
    return runtime


def market_descriptions() -> List[Dict[str, Any]]:
    return [
        {
            "symbol": market.symbol,
            "provider": market.provider,
            "asset_class": market.asset_class,
            "tick_size": market.tick_size,
        }
        for market in markets
    ]


@app.get("/api/markets")
def get_markets() -> List[Dict[str, Any]]:
    return market_descriptions()


@app.get("/api/health")
def get_health(symbol: Optional[str] = None) -> HealthStatus:
    return get_runtime(symbol).order_book.status


@app.get("/api/alerts")
def get_alerts(
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> List[AlertPayload]:
    return get_runtime(symbol).alerts(limit)


@app.get("/api/bars")
def get_completed_bars(symbol: Optional[str] = None) -> List[FootprintBar]:
    return get_runtime(symbol).completed_bars()


@app.websocket("/ws/orderflow")
async def orderflow_websocket(websocket: WebSocket, symbol: Optional[str] = None) -> None:
    selected_symbol = (symbol or default_symbol).strip().upper()
    runtime = market_runtimes.get(selected_symbol)
    if runtime is None:
        await websocket.close(code=1008, reason=f"Unknown market: {selected_symbol}")
        return

    await ConnectionManager.connect(websocket, selected_symbol)
    try:
        await websocket.send_text(json.dumps(runtime.initial_state(market_descriptions())))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ConnectionManager.disconnect(websocket)
    except Exception:
        logger.exception("WebSocket error for %s", selected_symbol)
        ConnectionManager.disconnect(websocket)


async def run_market_feed(runtime: MarketRuntime, adapter: MarketDataAdapter) -> None:
    symbol = runtime.market.symbol
    while True:
        try:
            async for event in adapter.stream(runtime.market):
                await ConnectionManager.broadcast(symbol, runtime.process_event(event))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("Market feed failed for %s", symbol)
            runtime.order_book.status.state = "DISCONNECTED"
            runtime.order_book.status.message = f"Feed error: {error}"
            await ConnectionManager.broadcast(
                symbol,
                {"type": "HEALTH_UPDATE", "health": runtime.order_book.status.model_dump()},
            )
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting market feeds for %s", ", ".join(market_runtimes))
    for symbol, runtime in market_runtimes.items():
        feed_tasks.append(asyncio.create_task(run_market_feed(runtime, market_adapters[symbol])))


@app.on_event("shutdown")
async def shutdown_event() -> None:
    for task in feed_tasks:
        task.cancel()
    if feed_tasks:
        await asyncio.gather(*feed_tasks, return_exceptions=True)
    feed_tasks.clear()