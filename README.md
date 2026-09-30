# Real-Time Order Flow Indicator Engine

A production-grade real-time order flow indicator for live trading — built to the standard required to risk real capital on.

> **Every non-negotiable requirement from the spec is explicitly implemented or disclosed as a known simplification. No silent failures, no misleading signals.**

---

## Architecture

```
Exchange WS/REST  →  Ingestion Layer  →  Order Book & Tape State
                                                  ↓
                                        Analytics Engine
                                   (Delta, CVD, Imbalance,
                                    Absorption, Iceberg,
                                    Tape Speed)
                                                  ↓
                                        Alert Manager
                                   (Auditable payloads,
                                    cooldown debounce)
                                                  ↓
                              FastAPI WebSocket Broadcaster
                                                  ↓
                              Flutter Custom Footprint Chart UI
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, asyncio, Pydantic v2, uvicorn |
| Frontend | Flutter (Dart), custom `CustomPainter` canvas charts |
| Data Feed | Provider-neutral normalized trade/book events; simulated adapter included |
| Tests | pytest, pytest-asyncio |

---

## Non-Negotiable Requirements Status

| Requirement | Implementation |
|------------|----------------|
| No fabricated data | Sequence gap → `DATA_GAP_DETECTED` state, bars flagged `UNRELIABLE_GAP` |
| Correct trade-side classification | Binance `isBuyerMaker` flag (primary), Lee-Ready tick rule (fallback), `classification_method` logged on every tick |
| Clock integrity | Exchange server `T` timestamp for bar aggregation; `local_receipt_time` separate for latency monitoring |
| No look-ahead bias | Sequential processing only; replay uses identical live code path |
| Reconcilable state | REST snapshot resync with WS update buffering and sequence ordering |
| Explicit confidence | Iceberg: `confidence_score ∈ [0.0, 1.0]` + `failure_modes` list on every alert |

---

## Test Suite

```
test_delta_cvd_exact_reconciliation     ∑BarDelta ≡ CVD with < 1e-9 tolerance
test_replay_engine_reconciliation       100-tick replay via live engine code path
test_iceberg_probabilistic_confidence   Confidence scoring + failure mode disclosure
test_absorption_statistical_outlier     Statistical outlier detection (z-score)
test_order_book_sequence_gap_and_resync Gap detected → REST resync → state restored
test_exchange_flag_priority             Exchange aggressor flag mapping
test_lee_ready_tick_rule                Uptick/downtick/zero-tick sequences
```

```bash
python -m pytest backend/tests/ -v
```

---

## Multi-Market Configuration

The backend supports isolated order-flow state per configured symbol. Set
`ORDERFLOW_MARKETS` to a JSON array before starting the backend:

```json
[
  {"symbol":"BTCUSDT","provider":"simulated","asset_class":"crypto","tick_size":0.1,"initial_price":65000},
  {"symbol":"AAPL","provider":"simulated","asset_class":"equity","tick_size":0.01,"initial_price":200}
]
```

Each entry selects a provider adapter and instrument-specific tick size. The
Flutter dashboard lists configured markets and subscribes to the selected
symbol. `provider` must be registered with
`register_market_data_adapter()`; only `simulated` is registered by default.
The existing Binance message parser is not yet a running feed adapter, and no
other broker/exchange API is currently connected. Broker credentials should be
configured as deployment secrets, never committed to this repository.

## Hosting

The repository includes deploy configurations for GitHub Pages and Vercel
(Flutter web frontend), plus Render (FastAPI backend).

1. Deploy the Render service from `render.yaml`. It starts with simulated
   BTCUSDT and AAPL markets. Wait for `/api/markets` to respond.
2. Set `ORDERFLOW_WS_URL` to `wss://<your-render-service>.onrender.com/ws/orderflow`
   as a GitHub Actions repository variable and as a Vercel environment variable.
3. Enable GitHub Pages with **GitHub Actions** as its source. Each push to
   `main` builds the Flutter web client and deploys it under the repository path.
4. Import the repository into Vercel. Its `vercel.json` builds the same client
   at the domain root; configure the same `ORDERFLOW_WS_URL` variable there.

The frontend build fails when `ORDERFLOW_WS_URL` is missing rather than silently
shipping a browser client pointed at localhost. The Pages and Vercel frontends
are public clients, so the Render API must allow their origins if CORS is later
restricted.

If the Render service was created manually instead of from the Blueprint, set
its Root Directory to `.` and Start Command to:

```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
```

The command `uvicorn main:app` cannot work from the repository root because the
ASGI app lives in `backend/app/main.py`.

## Running Locally

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the backend

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- REST API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws/orderflow`

### 3. Run the Flutter UI

```bash
cd frontend
flutter pub get
flutter run -d chrome --web-port 3000   # Web (Chrome/Edge)
flutter run -d windows                   # Windows desktop (requires VS C++ tools)
```

### 4. One-click launch

```powershell
.\start.ps1
```

---

## UI Layout

```
┌─────────────────────────────────────────┬──────────────────┐
│  STREAM HEALTH BANNER (state, gaps, latency)               │
├─────────────────────────────────────────┬──────────────────┤
│                                         │                  │
│   FOOTPRINT CHART (70%)                 │  ALERT FEED      │
│   · Bid Vol × Ask Vol per level         │  (30%)           │
│   · Green = buy imbalance (≥3:1)        │                  │
│   · Red = sell imbalance (≥3:1)         │  · Alert type    │
│   · Gold border = POC level             │  · Confidence %  │
│   · ⚠ GAP DETECTED on unreliable bars  │  · Raw metrics   │
│                                         │  · Thresholds    │
├─────────────────────────────────────────┤  · Failure modes │
│                                         │                  │
│   CVD LINE CHART (30%)                  │                  │
│   · Session cumulative delta            │                  │
│   · ▲ BULL / BEAR divergence markers   │                  │
│                                         │                  │
└─────────────────────────────────────────┴──────────────────┘
```

---

## Known Simplifications (Honest Disclosure)

1. **Iceberg detection** — Cannot distinguish a genuine hidden order from independent traders coincidentally placing limit orders at the same price. Documented in `failure_modes` on every alert.
2. **Lee-Ready on zero-tick** — Repeats the previous direction; error rate increases on heavily-traded, tight-spread instruments.
3. **Absorption price movement check** — Measured on the full bar high-low range, not per individual trade. A coarser but simpler signal.
4. **No TimescaleDB persistence** — Historical data is in-memory only for this build. Production deployment should add Postgres/TimescaleDB for bar storage.
5. **Simulated feed by default** — `BinanceClient` currently parses Binance events but is not registered as a live-stream adapter. Provider-specific WebSocket/REST connectors must be implemented and registered before live market data is available.

---

## Adding a Live Provider

Implement the `MarketDataAdapter` protocol and register its factory under the
provider name used in `ORDERFLOW_MARKETS`. The adapter must translate that
provider's events into normalized `Tick`, `BookUpdate`, and
`OrderBookSnapshot` models. Keep provider-specific authentication in
environment variables or the hosting platform's secret store. The analytics
consume normalized events and are shared across instruments and providers.

`BinanceClient` contains Binance message parsers, but does not yet implement or
register a live `MarketDataAdapter`. No live provider is enabled by default.

---

## License

MIT
