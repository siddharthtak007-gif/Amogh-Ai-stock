"""Typed payloads streamed to the frontend (orjson-serializable)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    FLAT = "FLAT"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


class Greeks(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float = 0.0
    iv: float = 0.0


class OptionContract(BaseModel):
    strike: float
    option_type: OptionType
    ltp: float
    bid: float
    ask: float
    oi: int
    oi_change: int = 0
    volume: int = 0
    iv: float = 0.0
    greeks: Greeks | None = None


class Candle(BaseModel):
    time: int  # unix seconds (TradingView Lightweight Charts)
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Signal(BaseModel):
    id: str
    timestamp: int
    underlying: str
    side: Side
    # Spot (underlying) levels
    entry: float
    stop_loss: float
    target: float
    target_2: float | None = None
    target_3: float | None = None
    trailing_sl: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rr_ratio: float
    reason: str
    predicted_levels: list[float] = Field(default_factory=list)
    discarded: bool = False
    discard_reason: str | None = None
    # F&O option leg — market niche jaaye to PE se profit
    option_type: OptionType | None = None
    option_strike: float | None = None
    option_ltp: float | None = None
    option_entry: float | None = None
    option_sl: float | None = None
    option_target: float | None = None
    option_target_2: float | None = None
    action_text: str = ""
    exit_text: str = ""
    direction_bias: str = ""  # BULLISH | BEARISH | NEUTRAL
    score: float = 0.0  # -1 .. +1



class ChainMetrics(BaseModel):
    pcr_oi: float
    pcr_volume: float
    max_pain: float
    vwap: float
    spot: float
    atm_iv: float
    oi_buildup_strikes: list[float] = Field(default_factory=list)
    volume_breakout: bool = False


class StreamPayload(BaseModel):
    """Combined WS frame: live OHLCV + AI overlay + chain snapshot."""

    type: Literal["tick", "candle", "signal", "chain", "heartbeat", "symbol_switch"] = "tick"
    ts: int
    underlying: str
    spot: float
    candle: Candle | None = None
    candles: list[Candle] = Field(default_factory=list)
    signal: Signal | None = None
    prediction: dict | None = None
    chain: list[OptionContract] = Field(default_factory=list)
    metrics: ChainMetrics | None = None
    instrument: dict | None = None
