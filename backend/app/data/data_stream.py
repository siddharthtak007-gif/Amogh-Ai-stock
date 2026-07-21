"""
Low-latency broker WebSocket ingestion + Redis tick/chain cache.

Supports DhanHQ / Fyers style binary/JSON feeds via a thin adapter,
with a deterministic mock feed for local development.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Deque

import numpy as np
import orjson
import redis.asyncio as aioredis
import websockets
from websockets.asyncio.client import ClientConnection

from app.config import Settings, get_settings
from app.models.schemas import Candle, OptionContract, OptionType

logger = logging.getLogger(__name__)


@dataclass
class TickBuffer:
    """Ring buffer for sub-second aggregation into OHLCV candles."""

    interval_sec: int = 60
    prices: Deque[float] = field(default_factory=lambda: deque(maxlen=50_000))
    volumes: Deque[float] = field(default_factory=lambda: deque(maxlen=50_000))
    times: Deque[float] = field(default_factory=lambda: deque(maxlen=50_000))
    candles: Deque[Candle] = field(default_factory=lambda: deque(maxlen=500))
    _open: float | None = None
    _high: float = -math.inf
    _low: float = math.inf
    _close: float = 0.0
    _vol: float = 0.0
    _bucket: int | None = None

    def push(self, price: float, volume: float = 0.0, ts: float | None = None) -> Candle | None:
        now = ts or time.time()
        bucket = int(now) // self.interval_sec * self.interval_sec
        self.prices.append(price)
        self.volumes.append(volume)
        self.times.append(now)

        closed: Candle | None = None
        if self._bucket is None:
            self._bucket = bucket
            self._open = price
            self._high = price
            self._low = price
            self._close = price
            self._vol = volume
            return None

        if bucket != self._bucket:
            closed = Candle(
                time=self._bucket,
                open=self._open or price,
                high=self._high,
                low=self._low,
                close=self._close,
                volume=self._vol,
            )
            self.candles.append(closed)
            self._bucket = bucket
            self._open = price
            self._high = price
            self._low = price
            self._close = price
            self._vol = volume
        else:
            self._high = max(self._high, price)
            self._low = min(self._low, price)
            self._close = price
            self._vol += volume
        return closed

    def current_partial(self) -> Candle | None:
        if self._bucket is None or self._open is None:
            return None
        return Candle(
            time=self._bucket,
            open=self._open,
            high=self._high if self._high != -math.inf else self._open,
            low=self._low if self._low != math.inf else self._open,
            close=self._close,
            volume=self._vol,
        )


class BrokerAdapter(ABC):
    @abstractmethod
    async def connect(self) -> AsyncIterator[dict[str, Any]]:
        ...

    @abstractmethod
    async def subscribe(self, instruments: list[str]) -> None:
        ...


class MockBrokerAdapter(BrokerAdapter):
    """Synthetic ticks + option-chain for any catalog symbol."""

    def __init__(self, symbol: str = "NIFTY", spot: float = 24_500.0, strike_step: float = 50.0):
        self.symbol = symbol.upper()
        self.spot = spot
        self.strike_step = strike_step
        self._running = True
        self._instruments: list[str] = [self.symbol]

    def switch(self, symbol: str, spot: float, strike_step: float) -> None:
        self.symbol = symbol.upper()
        self.spot = spot
        self.strike_step = strike_step
        self._instruments = [self.symbol]

    async def subscribe(self, instruments: list[str]) -> None:
        self._instruments = [i.upper() for i in instruments]
        if self._instruments:
            self.symbol = self._instruments[0]

    async def connect(self) -> AsyncIterator[dict[str, Any]]:
        rng = np.random.default_rng(42)
        while self._running:
            ret = float(rng.normal(0, 0.00035))
            self.spot *= 1.0 + ret
            vol = float(abs(rng.normal(1_200, 400)))
            ts = int(time.time())
            sym = self.symbol
            yield {
                "type": "spot",
                "underlying": sym,
                "ltp": round(self.spot, 2),
                "volume": vol,
                "ts": ts,
            }
            if ts % 1 == 0:
                yield {
                    "type": "option_chain",
                    "underlying": sym,
                    "spot": round(self.spot, 2),
                    "ts": ts,
                    "contracts": self._synthetic_chain(rng),
                }
            await asyncio.sleep(0.05)

    def _synthetic_chain(self, rng: np.random.Generator) -> list[dict[str, Any]]:
        atm = round(self.spot / self.strike_step) * self.strike_step
        rows: list[dict[str, Any]] = []
        for i in range(-8, 9):
            strike = atm + i * self.strike_step
            moneyness = (self.spot - strike) / self.spot
            for opt in ("CE", "PE"):
                intrinsic = max(0.0, self.spot - strike) if opt == "CE" else max(0.0, strike - self.spot)
                iv = 0.12 + abs(moneyness) * 0.8 + float(rng.uniform(0, 0.02))
                ltp = max(1.0, intrinsic + self.spot * iv * 0.04)
                oi = int(rng.integers(50_000, 2_500_000))
                rows.append(
                    {
                        "strike": round(strike, 2),
                        "option_type": opt,
                        "ltp": round(ltp, 2),
                        "bid": round(ltp * 0.995, 2),
                        "ask": round(ltp * 1.005, 2),
                        "oi": oi,
                        "oi_change": int(rng.integers(-80_000, 120_000)),
                        "volume": int(rng.integers(1_000, 500_000)),
                        "iv": round(iv, 4),
                    }
                )
        return rows


def _seed_candles(spot: float, n: int = 80, interval_sec: int = 60) -> list[Candle]:
    """Bootstrap chart history so UI is not blank after symbol switch."""
    rng = np.random.default_rng(abs(hash(str(spot))) % (2**32))
    now = int(time.time()) // interval_sec * interval_sec
    price = spot * (1.0 - 0.008)
    out: list[Candle] = []
    for i in range(n):
        ret = float(rng.normal(0, 0.0012))
        o = price
        c = price * (1.0 + ret)
        h = max(o, c) * (1.0 + abs(float(rng.normal(0, 0.0004))))
        l = min(o, c) * (1.0 - abs(float(rng.normal(0, 0.0004))))
        out.append(
            Candle(
                time=now - (n - i) * interval_sec,
                open=round(o, 2),
                high=round(h, 2),
                low=round(l, 2),
                close=round(c, 2),
                volume=float(abs(rng.normal(8_000, 2_000))),
            )
        )
        price = c
    return out


class DhanBrokerAdapter(BrokerAdapter):
    """
    DhanHQ market-feed WebSocket adapter.
    Docs: https://dhanhq.co/docs/v2/live-market-feed/
    Wire your access token + instrument list in Settings.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._ws: ClientConnection | None = None

    async def subscribe(self, instruments: list[str]) -> None:
        if not self._ws:
            return
        payload = {
            "RequestCode": 15,
            "InstrumentCount": len(instruments),
            "InstrumentList": [{"ExchangeSegment": "NSE_FNO", "SecurityId": i} for i in instruments],
        }
        await self._ws.send(orjson.dumps(payload).decode())

    async def connect(self) -> AsyncIterator[dict[str, Any]]:
        url = self.settings.broker_ws_url or "wss://api-feed.dhan.co"
        auth_qs = (
            f"?version=2&token={self.settings.broker_access_token}"
            f"&clientId={self.settings.broker_client_id}&authType=2"
        )
        async with websockets.connect(url + auth_qs, ping_interval=20, max_queue=1024) as ws:
            self._ws = ws
            async for raw in ws:
                msg = self._parse(raw)
                if msg:
                    yield msg

    def _parse(self, raw: str | bytes) -> dict[str, Any] | None:
        try:
            data = orjson.loads(raw)
        except Exception:
            return None
        # Normalize to internal schema — extend for binary packets as needed
        if isinstance(data, dict) and "LTP" in data:
            return {
                "type": "spot",
                "underlying": self.settings.underlying,
                "ltp": float(data["LTP"]),
                "volume": float(data.get("volume", 0)),
                "ts": int(time.time()),
            }
        return data if isinstance(data, dict) else None


def build_adapter(settings: Settings) -> BrokerAdapter:
    from app.instruments import get_instrument

    inst = get_instrument(settings.underlying)
    if settings.broker == "mock":
        if inst:
            return MockBrokerAdapter(inst.symbol, inst.base_spot, inst.strike_step)
        return MockBrokerAdapter(settings.underlying)
    if settings.broker == "dhan":
        return DhanBrokerAdapter(settings)
    logger.warning("Broker '%s' falling back to mock adapter", settings.broker)
    if inst:
        return MockBrokerAdapter(inst.symbol, inst.base_spot, inst.strike_step)
    return MockBrokerAdapter(settings.underlying)


class RedisTickCache:
    """Sub-millisecond get/set for live spot + option chain snapshots."""

    def __init__(self, redis: aioredis.Redis, settings: Settings):
        self.r = redis
        self.s = settings

    def _spot_key(self, underlying: str) -> str:
        return f"fo:spot:{underlying}"

    def _chain_key(self, underlying: str) -> str:
        return f"fo:chain:{underlying}"

    def _candle_key(self, underlying: str) -> str:
        return f"fo:candles:{underlying}"

    async def set_spot(self, underlying: str, ltp: float, volume: float, ts: int) -> None:
        payload = orjson.dumps({"ltp": ltp, "volume": volume, "ts": ts})
        await self.r.set(self._spot_key(underlying), payload, ex=self.s.redis_tick_ttl_sec)

    async def get_spot(self, underlying: str) -> dict[str, Any] | None:
        raw = await self.r.get(self._spot_key(underlying))
        return orjson.loads(raw) if raw else None

    async def set_chain(self, underlying: str, contracts: list[dict[str, Any]], spot: float) -> None:
        payload = orjson.dumps({"spot": spot, "contracts": contracts, "ts": int(time.time())})
        await self.r.set(self._chain_key(underlying), payload, ex=self.s.redis_chain_ttl_sec)

    async def get_chain(self, underlying: str) -> dict[str, Any] | None:
        raw = await self.r.get(self._chain_key(underlying))
        return orjson.loads(raw) if raw else None

    async def push_candle(self, underlying: str, candle: Candle) -> None:
        key = self._candle_key(underlying)
        await self.r.lpush(key, candle.model_dump_json())
        await self.r.ltrim(key, 0, 499)

    async def get_candles(self, underlying: str, n: int = 200) -> list[Candle]:
        raws = await self.r.lrange(self._candle_key(underlying), 0, n - 1)
        candles = [Candle.model_validate(orjson.loads(r)) for r in raws]
        candles.reverse()
        return candles


class DataStreamService:
    """
    Owns the broker connection, redis cache, and candle aggregation.
    Fan-out via asyncio.Queue for the FastAPI WebSocket layer.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.adapter = build_adapter(self.settings)
        self.buffer = TickBuffer(interval_sec=60)
        self.subscribers: list[asyncio.Queue[dict[str, Any]]] = []
        self._redis: aioredis.Redis | None = None
        self.cache: RedisTickCache | None = None
        self._task: asyncio.Task | None = None
        self.latest_spot: float = 0.0
        self.latest_chain: list[OptionContract] = []
        self.active_underlying: str = self.settings.underlying.upper()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        try:
            self._redis = aioredis.from_url(self.settings.redis_url, decode_responses=False)
            await self._redis.ping()
            self.cache = RedisTickCache(self._redis, self.settings)
            logger.info("Redis connected: %s", self.settings.redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — running without cache", exc)
            self.cache = None

        await self.adapter.subscribe([self.active_underlying])
        # Seed chart so first paint is not empty
        from app.instruments import get_instrument

        inst = get_instrument(self.active_underlying)
        base = inst.base_spot if inst else 24_500.0
        for c in _seed_candles(base):
            self.buffer.candles.append(c)
        self.latest_spot = base
        self._task = asyncio.create_task(self._ingest_loop(), name="data-ingest")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()

    async def switch_underlying(self, symbol: str) -> dict[str, Any]:
        """Hot-switch active symbol — resets candles / chain and retargets mock feed."""
        from app.instruments import get_instrument

        sym = symbol.strip().upper()
        inst = get_instrument(sym)
        if not inst:
            raise ValueError(f"Unknown instrument: {symbol}")

        async with self._lock:
            self.active_underlying = inst.symbol
            self.settings.underlying = inst.symbol
            self.buffer = TickBuffer(interval_sec=60)
            for c in _seed_candles(inst.base_spot):
                self.buffer.candles.append(c)
            self.latest_spot = inst.base_spot
            self.latest_chain = []

            if isinstance(self.adapter, MockBrokerAdapter):
                self.adapter.switch(inst.symbol, inst.base_spot, inst.strike_step)
            await self.adapter.subscribe([inst.symbol])

            await self._broadcast(
                {
                    "type": "symbol_switch",
                    "underlying": inst.symbol,
                    "spot": inst.base_spot,
                    "ts": int(time.time()),
                    "candle": self.buffer.current_partial(),
                    "candles": list(self.buffer.candles),
                    "contracts": [],
                    "instrument": {
                        "symbol": inst.symbol,
                        "name": inst.name,
                        "segment": inst.segment,
                        "lot_size": inst.lot_size,
                    },
                }
            )

        logger.info("Switched underlying → %s (%.2f)", inst.symbol, inst.base_spot)
        return {
            "symbol": inst.symbol,
            "name": inst.name,
            "segment": inst.segment,
            "spot": inst.base_spot,
            "lot_size": inst.lot_size,
        }

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)

    async def _broadcast(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for q in self.subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    async def _ingest_loop(self) -> None:
        async for msg in self.adapter.connect():
            underlying = str(msg.get("underlying") or self.active_underlying).upper()
            # Ignore ticks for a previous symbol mid-switch
            if underlying != self.active_underlying:
                continue

            mtype = msg.get("type")
            if mtype == "spot":
                ltp = float(msg["ltp"])
                volume = float(msg.get("volume", 0))
                ts = int(msg.get("ts", time.time()))
                self.latest_spot = ltp
                closed = self.buffer.push(ltp, volume, ts)
                if self.cache:
                    await self.cache.set_spot(underlying, ltp, volume, ts)
                    if closed:
                        await self.cache.push_candle(underlying, closed)

                event: dict[str, Any] = {
                    "type": "tick",
                    "underlying": underlying,
                    "spot": ltp,
                    "volume": volume,
                    "ts": ts,
                    "candle": (closed or self.buffer.current_partial()),
                    "candles": list(self.buffer.candles)[-120:],
                }
                await self._broadcast(event)

            elif mtype == "option_chain":
                contracts = [
                    OptionContract(
                        strike=c["strike"],
                        option_type=OptionType(c["option_type"]),
                        ltp=c["ltp"],
                        bid=c["bid"],
                        ask=c["ask"],
                        oi=c["oi"],
                        oi_change=c.get("oi_change", 0),
                        volume=c.get("volume", 0),
                        iv=c.get("iv", 0.0),
                    )
                    for c in msg.get("contracts", [])
                ]
                self.latest_chain = contracts
                spot = float(msg.get("spot", self.latest_spot))
                if self.cache:
                    await self.cache.set_chain(
                        underlying,
                        [c.model_dump() for c in contracts],
                        spot,
                    )
                await self._broadcast(
                    {
                        "type": "chain",
                        "underlying": underlying,
                        "spot": spot,
                        "ts": int(msg.get("ts", time.time())),
                        "contracts": contracts,
                    }
                )
