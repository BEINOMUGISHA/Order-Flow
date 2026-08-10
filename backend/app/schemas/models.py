from typing import Dict, List, Tuple, Literal, Optional, Any
from pydantic import BaseModel, Field


class Tick(BaseModel):
    symbol: str
    price: float
    quantity: float
    trade_id: str
    aggressor_side: Literal["BUY", "SELL"]
    exchange_time: int  # ms timestamp from exchange
    local_receipt_time: float  # time.time() timestamp
    sequence_id: Optional[int] = None
    classification_method: Literal["EXCHANGE_FLAG", "LEE_READY_TICK_RULE"]


class BookUpdate(BaseModel):
    symbol: str
    first_update_id: int
    final_update_id: int
    pu_final_update_id: Optional[int] = None  # previous u for Binance Futures
    bids: List[Tuple[float, float]]  # (price, quantity)
    asks: List[Tuple[float, float]]  # (price, quantity)
    exchange_time: int


class OrderBookSnapshot(BaseModel):
    symbol: str
    last_update_id: int
    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]


class FootprintLevel(BaseModel):
    price: float
    bid_vol: float = 0.0
    ask_vol: float = 0.0
    total_vol: float = 0.0
    delta: float = 0.0
    imbalance_flag: Literal["BUY_IMBALANCE", "SELL_IMBALANCE", "NONE"] = "NONE"


class FootprintBar(BaseModel):
    bar_id: str
    start_time: int
    end_time: int
    open: float
    high: float
    low: float
    close: float
    total_volume: float = 0.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    delta: float = 0.0
    cvd: float = 0.0
    poc_price: float = 0.0
    levels: Dict[str, FootprintLevel] = Field(default_factory=dict)
    gap_flag: bool = False
    confidence: Literal["CONFIDENT", "UNRELIABLE_GAP"] = "CONFIDENT"


class AlertPayload(BaseModel):
    alert_id: str
    alert_type: Literal[
        "CVD_PRICE_DIVERGENCE",
        "IMBALANCE_BREACH",
        "ABSORPTION_EVENT",
        "ICEBERG_DETECTED",
        "TAPE_SPEED_SPIKE",
    ]
    timestamp: int
    symbol: str
    price: float
    raw_metrics: Dict[str, Any]
    threshold_used: Dict[str, Any]
    confidence_score: float  # 0.0 to 1.0
    confidence_tier: Literal["HIGH", "MEDIUM", "LOW", "UNRELIABLE"]
    failure_modes: List[str] = Field(default_factory=list)
    is_debounced: bool = False


class HealthStatus(BaseModel):
    state: Literal["OK", "DATA_GAP_DETECTED", "RESYNCING", "DISCONNECTED"] = "OK"
    gap_count: int = 0
    last_sequence_id: Optional[int] = None
    avg_latency_ms: float = 0.0
    last_resync_timestamp: Optional[int] = None
    message: str = "System Operating Normally"
