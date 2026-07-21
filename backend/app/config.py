"""Application configuration — env-driven for low-latency F&O stack."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FO Predictive Analytics"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Broker — DhanHQ / Fyers / Zerodha (adapter selected at runtime)
    broker: Literal["dhan", "fyers", "zerodha", "mock"] = "mock"
    broker_client_id: str = ""
    broker_access_token: str = ""
    broker_api_key: str = ""
    broker_api_secret: str = ""
    broker_ws_url: str = ""

    # Instruments — any F&O symbol from instruments catalog
    underlying: str = "NIFTY"
    expiry: str = ""  # YYYY-MM-DD; empty = nearest weekly

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_tick_ttl_sec: int = 5
    redis_chain_ttl_sec: int = 3

    # Quant / Risk
    risk_free_rate: float = 0.07
    min_rr_ratio: float = 2.0  # discard if RR < 1:2 on T1
    oi_buildup_threshold_pct: float = 8.0
    volume_breakout_zscore: float = 2.5
    # Spot levels (ATR multiples)
    default_sl_atr_mult: float = 1.0
    default_target_atr_mult: float = 2.0
    target2_atr_mult: float = 3.0
    target3_atr_mult: float = 4.0
    # Option premium (buy CE / buy PE)
    option_sl_pct: float = 0.35
    option_tgt1_pct: float = 0.70
    option_tgt2_pct: float = 1.20

    # ML
    ml_model_path: str = "models/confidence_rf.joblib"
    confidence_threshold: float = 0.55
    signal_cooldown_sec: int = 20

    # WebSocket fan-out
    broadcast_hz: float = 8.0
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
