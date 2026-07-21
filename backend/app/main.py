"""FastAPI app — low-latency WebSocket fan-out of OHLCV + AI signals."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import orjson
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.data.data_stream import DataStreamService
from app.instruments import get_instrument, list_all, search_instruments
from app.models.schemas import Candle, StreamPayload
from app.quant.quant_engine import QuantEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("fo.main")
settings = get_settings()

stream = DataStreamService(settings)
engine = QuantEngine(settings)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.active.discard(ws)

    async def broadcast_bytes(self, payload: bytes) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.active):
            try:
                await ws.send_bytes(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


def _as_candle(c: Candle | dict[str, Any] | None) -> Candle | None:
    if c is None:
        return None
    return c if isinstance(c, Candle) else Candle.model_validate(c)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await stream.start()
    fanout_task = asyncio.create_task(_analytics_fanout(), name="analytics-fanout")
    logger.info("FO Predictive Analytics online | broker=%s", settings.broker)
    try:
        yield
    finally:
        fanout_task.cancel()
        try:
            await fanout_task
        except asyncio.CancelledError:
            pass
        await stream.stop()


app = FastAPI(
    title=settings.app_name,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _analytics_fanout() -> None:
    """
    Consume ingest events → run quant engine → push combined frames.
    Rate-limited to settings.broadcast_hz to protect frontend render loop.
    """
    q = stream.subscribe()
    min_interval = 1.0 / max(settings.broadcast_hz, 1.0)
    last_push = 0.0
    last_metrics = None
    last_chain = []

    try:
        while True:
            event = await q.get()
            now = time.time()
            etype = event.get("type")
            underlying = event.get("underlying", settings.underlying)
            spot = float(event.get("spot") or stream.latest_spot or 0.0)
            candles: list[Candle] = event.get("candles") or list(stream.buffer.candles)
            candle = event.get("candle")

            signal = None
            prediction = None

            if etype == "symbol_switch":
                # Reset local analytics state for new symbol
                last_chain = []
                last_metrics = None
                engine.active_signal = None
                engine._last_signal_ts = 0
                engine.latest_live_plan = None
                prediction = engine.snapshot_prediction(spot, None)

            elif etype == "chain":
                contracts = event.get("contracts") or []
                enriched, metrics = engine.analyze_chain(contracts, spot, candles)
                last_chain = enriched
                last_metrics = metrics
                signal = engine.generate_signal(underlying, spot, candles, enriched, metrics)
                prediction = engine.snapshot_prediction(spot, signal)

            elif etype == "tick" and last_metrics is not None and last_chain:
                signal = engine.generate_signal(
                    underlying, spot, candles, last_chain, last_metrics
                )
                prediction = engine.snapshot_prediction(spot, signal)

            if now - last_push < min_interval and etype == "tick":
                continue

            allowed = ("chain", "signal", "heartbeat", "symbol_switch")
            frame_type = "candle" if etype == "tick" else (etype if etype in allowed else "tick")
            payload = StreamPayload(
                type=frame_type,  # type: ignore[arg-type]
                ts=int(event.get("ts", now)),
                underlying=underlying,
                spot=spot,
                candle=_as_candle(candle),
                candles=candles[-120:],
                signal=signal,
                prediction=prediction,
                chain=last_chain[:40],
                metrics=last_metrics,
                instrument=event.get("instrument"),
            )

            # Prefer orjson bytes for minimal serialization cost
            body = orjson.dumps(payload.model_dump(mode="json"))
            await manager.broadcast_bytes(body)
            last_push = now
    finally:
        stream.unsubscribe(q)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "spot": stream.latest_spot,
        "underlying": stream.active_underlying,
        "subscribers": len(manager.active),
        "broker": settings.broker,
    }


class SelectSymbolBody(BaseModel):
    symbol: str = Field(..., min_length=1, examples=["BANKNIFTY", "RELIANCE"])


@app.get("/api/instruments")
async def instruments(q: str = Query("", description="Search by symbol or company name")) -> dict[str, Any]:
    hits = search_instruments(q)
    return {
        "query": q,
        "count": len(hits),
        "results": [
            {
                "symbol": i.symbol,
                "name": i.name,
                "segment": i.segment,
                "base_spot": i.base_spot,
                "lot_size": i.lot_size,
                "exchange": i.exchange,
            }
            for i in hits
        ],
    }


@app.get("/api/instruments/all")
async def instruments_all() -> dict[str, Any]:
    return {"results": list_all()}


@app.post("/api/instruments/select")
async def select_instrument(body: SelectSymbolBody) -> dict[str, Any]:
    try:
        info = await stream.switch_underlying(body.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Force fresh prediction cycle
    engine.active_signal = None
    engine._last_signal_ts = 0
    return {"ok": True, "instrument": info}


@app.get("/api/snapshot")
async def snapshot() -> JSONResponse:
    candles = list(stream.buffer.candles)[-120:]
    contracts = stream.latest_chain
    spot = stream.latest_spot
    enriched, metrics = engine.analyze_chain(contracts, spot, candles) if contracts else ([], None)
    inst = get_instrument(stream.active_underlying)
    return ORJSONResponse(
        {
            "underlying": stream.active_underlying,
            "spot": spot,
            "candles": [c.model_dump() for c in candles],
            "chain": [c.model_dump() for c in enriched[:40]],
            "metrics": metrics.model_dump() if metrics else None,
            "prediction": engine.snapshot_prediction(spot, engine.active_signal),
            "instrument": {
                "symbol": inst.symbol,
                "name": inst.name,
                "segment": inst.segment,
                "lot_size": inst.lot_size,
            }
            if inst
            else None,
        }
    )


@app.websocket("/ws/market")
async def market_ws(ws: WebSocket) -> None:
    await manager.connect(ws)
    logger.info("WS client connected (%d total)", len(manager.active))
    try:
        inst = get_instrument(stream.active_underlying)
        snap = {
            "type": "heartbeat",
            "ts": int(time.time()),
            "underlying": stream.active_underlying,
            "spot": stream.latest_spot,
            "candles": [c.model_dump() for c in list(stream.buffer.candles)[-120:]],
            "prediction": engine.snapshot_prediction(stream.latest_spot, engine.active_signal),
            "chain": [c.model_dump() for c in stream.latest_chain[:40]],
            "instrument": {
                "symbol": inst.symbol,
                "name": inst.name,
                "segment": inst.segment,
                "lot_size": inst.lot_size,
            }
            if inst
            else None,
        }
        await ws.send_bytes(orjson.dumps(snap))

        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if msg == "ping":
                    await ws.send_bytes(
                        orjson.dumps(
                            {
                                "type": "heartbeat",
                                "ts": int(time.time()),
                                "underlying": stream.active_underlying,
                                "spot": stream.latest_spot,
                            }
                        )
                    )
                    continue
                # Client commands: {"action":"subscribe","symbol":"RELIANCE"}
                try:
                    cmd = orjson.loads(msg)
                except Exception:
                    continue
                if isinstance(cmd, dict) and cmd.get("action") == "subscribe":
                    symbol = str(cmd.get("symbol", "")).strip()
                    try:
                        info = await stream.switch_underlying(symbol)
                        engine.active_signal = None
                        engine._last_signal_ts = 0
                        await ws.send_bytes(
                            orjson.dumps(
                                {
                                    "type": "symbol_switch",
                                    "ts": int(time.time()),
                                    "underlying": info["symbol"],
                                    "spot": info["spot"],
                                    "instrument": info,
                                    "ok": True,
                                }
                            )
                        )
                    except ValueError as exc:
                        await ws.send_bytes(
                            orjson.dumps({"type": "error", "message": str(exc), "ts": int(time.time())})
                        )
            except asyncio.TimeoutError:
                await ws.send_bytes(
                    orjson.dumps(
                        {
                            "type": "heartbeat",
                            "ts": int(time.time()),
                            "underlying": stream.active_underlying,
                            "spot": stream.latest_spot,
                        }
                    )
                )
    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    finally:
        await manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        loop="asyncio",
        http="httptools",
        ws="websockets",
        log_level="info",
    )
