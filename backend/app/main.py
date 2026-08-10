import asyncio
import json
import logging
import random
import time
from typing import List, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas.models import Tick, BookUpdate, OrderBookSnapshot, FootprintBar, AlertPayload, HealthStatus
from app.state.order_book import OrderBook
from app.state.tape_buffer import RollingTapeBuffer
from app.analytics.delta_engine import DeltaEngine
from app.analytics.absorption_engine import AbsorptionEngine
from app.analytics.iceberg_engine import IcebergEngine
from app.analytics.imbalance_engine import ImbalanceEngine
from app.analytics.tape_speed_engine import TapeSpeedEngine
from app.alerts.alert_manager import AlertManager
from app.ingestion.binance_client import BinanceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OrderFlowApp")

app = FastAPI(title="Real-Time Order Flow Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State & Engines
SYMBOL = "BTCUSDT"
order_book = OrderBook(SYMBOL)
tape_buffer = RollingTapeBuffer()
delta_engine = DeltaEngine(symbol=SYMBOL, tick_size=0.1)
absorption_engine = AbsorptionEngine(tick_size=0.1)
iceberg_engine = IcebergEngine()
imbalance_engine = ImbalanceEngine()
tape_speed_engine = TapeSpeedEngine()
alert_manager = AlertManager()
binance_client = BinanceClient(symbol=SYMBOL, is_futures=True)

active_connections: Set[WebSocket] = set()


class ConnectionManager:
    @staticmethod
    async def connect(websocket: WebSocket):
        await websocket.accept()
        active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(active_connections)}")

    @staticmethod
    def disconnect(websocket: WebSocket):
        active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(active_connections)}")

    @staticmethod
    async def broadcast(message: dict):
        if not active_connections:
            return
        payload = json.dumps(message)
        disconnected = set()
        for conn in active_connections:
            try:
                await conn.send_text(payload)
            except Exception:
                disconnected.add(conn)
        for conn in disconnected:
            active_connections.remove(conn)


@app.get("/api/health")
def get_health() -> HealthStatus:
    return order_book.status


@app.get("/api/alerts")
def get_alerts(limit: int = 50) -> List[AlertPayload]:
    return alert_manager.get_audit_log(limit=limit)


@app.get("/api/bars")
def get_completed_bars() -> List[FootprintBar]:
    return delta_engine.completed_bars


@app.websocket("/ws/orderflow")
async def orderflow_websocket(websocket: WebSocket):
    await ConnectionManager.connect(websocket)
    try:
        # Send initial state snapshot
        initial_payload = {
            "type": "INITIAL_STATE",
            "health": order_book.status.model_dump(),
            "completed_bars": [b.model_dump() for b in delta_engine.completed_bars[-20:]],
            "active_bar": delta_engine.current_bar.model_dump() if delta_engine.current_bar else None,
            "session_cvd": delta_engine.session_cvd,
            "alerts": [a.model_dump() for a in alert_manager.get_audit_log(20)],
        }
        await websocket.send_text(json.dumps(initial_payload))

        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ConnectionManager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ConnectionManager.disconnect(websocket)


async def simulated_tick_generator():
    """
    High-frequency realistic order flow generator for live testing/demoing
    when live exchange feeds are offline or for benchmark testing.
    """
    current_price = 65000.0
    tick_id = 1000
    base_time = int(time.time() * 1000)

    # Initialize snapshot in order book
    order_book.apply_snapshot(
        OrderBookSnapshot(
            symbol=SYMBOL,
            last_update_id=100,
            bids=[(current_price - i * 0.1, round(random.uniform(0.5, 5.0), 2)) for i in range(10)],
            asks=[(current_price + i * 0.1, round(random.uniform(0.5, 5.0), 2)) for i in range(10)],
        )
    )

    while True:
        await asyncio.sleep(random.uniform(0.05, 0.2))  # 5 to 20 trades per sec

        # Price movement random walk
        step = random.choice([-0.1, 0.0, 0.0, 0.1])
        current_price = round(current_price + step, 1)

        side = random.choice(["BUY", "SELL"])
        # Occasionally generate large outlier trade for absorption
        if random.random() < 0.05:
            qty = round(random.uniform(8.0, 15.0), 2)
        else:
            qty = round(random.uniform(0.01, 1.5), 2)

        tick_id += 1
        now_ms = int(time.time() * 1000)

        tick = Tick(
            symbol=SYMBOL,
            price=current_price,
            quantity=qty,
            trade_id=str(tick_id),
            aggressor_side=side,
            exchange_time=now_ms,
            local_receipt_time=time.time(),
            classification_method="EXCHANGE_FLAG",
        )

        tape_buffer.add_tick(tick)
        completed_bar, active_bar = delta_engine.process_tick(tick)

        alerts = []

        # Check absorption
        abs_alert = absorption_engine.check_absorption(tick, tape_buffer, active_bar)
        if abs_alert:
            p = alert_manager.process_alert(abs_alert)
            if p:
                alerts.append(p)

        # Check iceberg
        ice_alert = iceberg_engine.check_iceberg(tick, order_book, active_bar)
        if ice_alert:
            p = alert_manager.process_alert(ice_alert)
            if p:
                alerts.append(p)

        # Check tape speed
        tsp_alert = tape_speed_engine.check_tape_speed(tick, tape_buffer)
        if tsp_alert:
            p = alert_manager.process_alert(tsp_alert)
            if p:
                alerts.append(p)

        # Check imbalances on completed bar
        if completed_bar:
            imb_alerts = imbalance_engine.evaluate_bar_imbalances(completed_bar)
            for imb in imb_alerts:
                p = alert_manager.process_alert(imb)
                if p:
                    alerts.append(p)

        # Broadcast state update
        msg = {
            "type": "TICK_UPDATE",
            "tick": tick.model_dump(),
            "active_bar": active_bar.model_dump(),
            "completed_bar": completed_bar.model_dump() if completed_bar else None,
            "session_cvd": active_bar.cvd,
            "health": order_book.status.model_dump(),
            "alerts": [a.model_dump() for a in alerts],
        }
        await ConnectionManager.broadcast(msg)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Real-Time Order Flow Engine background task...")
    asyncio.create_task(simulated_tick_generator())
