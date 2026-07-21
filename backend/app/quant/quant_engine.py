"""
Quantitative engine: Black-Scholes Greeks, PCR, Max Pain, VWAP,
OI buildup / volume breakout detection, ML confidence + trajectory,
and hard risk gates (RR ≥ 1:2, SL / trailing SL).
"""

from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import norm
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from app.config import Settings, get_settings
from app.models.schemas import (
    Candle,
    ChainMetrics,
    Greeks,
    OptionContract,
    OptionType,
    Side,
    Signal,
)

logger = logging.getLogger(__name__)

# Optional: py_vollib accelerates IV/greeks when installed
try:
    from py_vollib.black_scholes.greeks.analytical import (
        delta as vollib_delta,
        gamma as vollib_gamma,
        rho as vollib_rho,
        theta as vollib_theta,
        vega as vollib_vega,
    )
    from py_vollib.black_scholes.implied_volatility import implied_volatility as vollib_iv

    HAS_VOLLIB = True
except ImportError:  # pragma: no cover
    HAS_VOLLIB = False


# ─────────────────────────────────────────────────────────────────────────────
# Black-Scholes (fallback when py_vollib missing / for vectorized batch)
# ─────────────────────────────────────────────────────────────────────────────


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0, 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    flag: str,  # 'c' | 'p'
) -> Greeks:
    flag = flag.lower()[0]
    if HAS_VOLLIB and T > 0 and sigma > 0:
        return Greeks(
            delta=float(vollib_delta(flag, S, K, T, r, sigma)),
            gamma=float(vollib_gamma(flag, S, K, T, r, sigma)),
            theta=float(vollib_theta(flag, S, K, T, r, sigma)),
            vega=float(vollib_vega(flag, S, K, T, r, sigma)),
            rho=float(vollib_rho(flag, S, K, T, r, sigma)),
            iv=sigma,
        )

    d1, d2 = _d1_d2(S, K, T, r, sigma)
    pdf = norm.pdf(d1)
    sqrt_t = math.sqrt(max(T, 1e-12))
    gamma = pdf / (S * sigma * sqrt_t) if S > 0 and sigma > 0 else 0.0
    vega = S * pdf * sqrt_t / 100.0  # per 1% IV
    if flag == "c":
        delta = norm.cdf(d1)
        theta = (
            -(S * pdf * sigma) / (2 * sqrt_t) - r * K * math.exp(-r * T) * norm.cdf(d2)
        ) / 365.0
        rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100.0
    else:
        delta = -norm.cdf(-d1)
        theta = (
            -(S * pdf * sigma) / (2 * sqrt_t) + r * K * math.exp(-r * T) * norm.cdf(-d2)
        ) / 365.0
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100.0
    return Greeks(delta=delta, gamma=gamma, theta=theta, vega=vega, rho=rho, iv=sigma)


def years_to_expiry(expiry_yyyy_mm_dd: str | None, now: float | None = None) -> float:
    if not expiry_yyyy_mm_dd:
        # Default: ~7 calendar days (weekly expiry proxy)
        return 7.0 / 365.0
    now = now or time.time()
    try:
        y, m, d = map(int, expiry_yyyy_mm_dd.split("-"))
        import datetime as dt

        exp = dt.datetime(y, m, d, 15, 30, tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
        T = (exp.timestamp() - now) / (365.0 * 24 * 3600)
        return max(T, 1e-6)
    except Exception:
        return 7.0 / 365.0


# ─────────────────────────────────────────────────────────────────────────────
# Chain analytics
# ─────────────────────────────────────────────────────────────────────────────


def put_call_ratio(contracts: list[OptionContract]) -> tuple[float, float]:
    ce_oi = sum(c.oi for c in contracts if c.option_type == OptionType.CE)
    pe_oi = sum(c.oi for c in contracts if c.option_type == OptionType.PE)
    ce_vol = sum(c.volume for c in contracts if c.option_type == OptionType.CE)
    pe_vol = sum(c.volume for c in contracts if c.option_type == OptionType.PE)
    pcr_oi = pe_oi / ce_oi if ce_oi else 0.0
    pcr_vol = pe_vol / ce_vol if ce_vol else 0.0
    return pcr_oi, pcr_vol


def max_pain(contracts: list[OptionContract]) -> float:
    """Strike minimizing total option writer pain (OI-weighted intrinsic)."""
    strikes = sorted({c.strike for c in contracts})
    if not strikes:
        return 0.0
    best_strike, best_pain = strikes[0], float("inf")
    for S in strikes:
        pain = 0.0
        for c in contracts:
            if c.option_type == OptionType.CE:
                pain += c.oi * max(0.0, S - c.strike)
            else:
                pain += c.oi * max(0.0, c.strike - S)
        if pain < best_pain:
            best_pain, best_strike = pain, S
    return best_strike


def vwap_from_candles(candles: list[Candle]) -> float:
    if not candles:
        return 0.0
    num = sum(((c.high + c.low + c.close) / 3.0) * c.volume for c in candles)
    den = sum(c.volume for c in candles)
    return num / den if den else candles[-1].close


def detect_oi_buildup(
    contracts: list[OptionContract],
    threshold_pct: float,
) -> list[float]:
    flagged: list[float] = []
    for c in contracts:
        if c.oi <= 0:
            continue
        pct = 100.0 * c.oi_change / max(c.oi - c.oi_change, 1)
        if abs(pct) >= threshold_pct:
            flagged.append(c.strike)
    return sorted(set(flagged))


def volume_breakout(candles: list[Candle], z_thresh: float = 2.5) -> bool:
    if len(candles) < 20:
        return False
    vols = np.array([c.volume for c in candles[-40:]], dtype=float)
    mu, sigma = vols[:-1].mean(), vols[:-1].std()
    if sigma < 1e-9:
        return False
    return (vols[-1] - mu) / sigma >= z_thresh


def enrich_chain_greeks(
    contracts: list[OptionContract],
    spot: float,
    r: float,
    T: float,
) -> list[OptionContract]:
    out: list[OptionContract] = []
    for c in contracts:
        sigma = c.iv if c.iv > 0 else 0.15
        flag = "c" if c.option_type == OptionType.CE else "p"
        g = bs_greeks(spot, c.strike, T, r, sigma, flag)
        out.append(c.model_copy(update={"greeks": g, "iv": sigma}))
    return out


def atm_iv(contracts: list[OptionContract], spot: float) -> float:
    if not contracts:
        return 0.0
    nearest = min(contracts, key=lambda c: abs(c.strike - spot))
    return nearest.iv


# ─────────────────────────────────────────────────────────────────────────────
# Technical features + ML skeleton
# ─────────────────────────────────────────────────────────────────────────────


def _ema(series: np.ndarray, span: int) -> np.ndarray:
    alpha = 2 / (span + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    delta = np.diff(closes[-(period + 1) :])
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = gains.mean()
    avg_loss = losses.mean()
    if avg_loss < 1e-12:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    window = trs[-period:]
    return float(np.mean(window)) if window else 0.0


@dataclass
class FeatureVector:
    rsi: float
    ema_spread: float
    atr_pct: float
    vwap_dist: float
    pcr_oi: float
    atm_iv: float
    oi_pressure: float  # + call buildup / - put buildup proxy
    volume_z: float


def build_features(
    candles: list[Candle],
    metrics: ChainMetrics,
    contracts: list[OptionContract],
) -> FeatureVector:
    closes = np.array([c.close for c in candles], dtype=float) if candles else np.array([metrics.spot])
    spot = closes[-1] if len(closes) else metrics.spot
    ema9 = _ema(closes, 9)[-1] if len(closes) else spot
    ema21 = _ema(closes, 21)[-1] if len(closes) else spot
    atr = _atr(candles)
    vols = np.array([c.volume for c in candles[-40:]], dtype=float) if candles else np.array([0.0])
    vol_z = 0.0
    if len(vols) >= 10 and vols[:-1].std() > 0:
        vol_z = float((vols[-1] - vols[:-1].mean()) / vols[:-1].std())

    call_oi_ch = sum(c.oi_change for c in contracts if c.option_type == OptionType.CE)
    put_oi_ch = sum(c.oi_change for c in contracts if c.option_type == OptionType.PE)
    oi_pressure = (call_oi_ch - put_oi_ch) / max(abs(call_oi_ch) + abs(put_oi_ch), 1)

    return FeatureVector(
        rsi=_rsi(closes),
        ema_spread=(ema9 - ema21) / spot if spot else 0.0,
        atr_pct=(atr / spot) if spot else 0.0,
        vwap_dist=(spot - metrics.vwap) / spot if metrics.vwap and spot else 0.0,
        pcr_oi=metrics.pcr_oi,
        atm_iv=metrics.atm_iv,
        oi_pressure=oi_pressure,
        volume_z=vol_z,
    )


class ConfidenceModel:
    """
    RandomForest skeleton for trade-direction probability + price trajectory.
    Trains on synthetic labels until you plug in labeled historical dumps.
    Persist via joblib when a real model is fitted.
    """

    FEATURE_ORDER = [
        "rsi",
        "ema_spread",
        "atr_pct",
        "vwap_dist",
        "pcr_oi",
        "atm_iv",
        "oi_pressure",
        "volume_z",
    ]

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.scaler = StandardScaler()
        self.clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42,
            class_weight="balanced",
        )
        self.reg = RandomForestRegressor(
            n_estimators=150,
            max_depth=6,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42,
        )
        self._fitted = False
        self._bootstrap()

    def _vec(self, f: FeatureVector) -> np.ndarray:
        return np.array(
            [
                [
                    f.rsi,
                    f.ema_spread,
                    f.atr_pct,
                    f.vwap_dist,
                    f.pcr_oi,
                    f.atm_iv,
                    f.oi_pressure,
                    f.volume_z,
                ]
            ],
            dtype=float,
        )

    def _bootstrap(self) -> None:
        """Self-supervised prior so the API works before real training data."""
        rng = np.random.default_rng(7)
        n = 2_000
        X = rng.normal(size=(n, len(self.FEATURE_ORDER)))
        # Heuristic labels: long when EMA spread + PCR elevated + RSI mid
        y = (
            (X[:, 1] > 0).astype(int)  # ema_spread
            ^ (X[:, 4] > 0.2).astype(int)  # pcr noise
        )
        # Trajectory residual ~ ATR-ish
        y_ret = 0.0015 * X[:, 1] - 0.0008 * (X[:, 0] - 0) + rng.normal(0, 0.0004, n)

        Xs = self.scaler.fit_transform(X)
        self.clf.fit(Xs, y)
        self.reg.fit(Xs, y_ret)
        self._fitted = True
        logger.info("ConfidenceModel bootstrapped (synthetic prior)")

    def predict(self, f: FeatureVector) -> tuple[float, Side, list[float]]:
        """
        Returns (confidence 0-1, side, predicted_levels[3]).
        Confidence = P(aligned class); trajectory = spot * (1 + k*ret_hat).
        """
        if not self._fitted:
            return 0.5, Side.FLAT, []

        x = self.scaler.transform(self._vec(f))
        proba = self.clf.predict_proba(x)[0]
        # classes_ may be [0,1] → 1 = bullish prior
        classes = list(self.clf.classes_)
        p_up = float(proba[classes.index(1)]) if 1 in classes else float(proba.max())
        ret_hat = float(self.reg.predict(x)[0])

        if p_up >= 0.55:
            side = Side.BUY
            confidence = p_up
        elif p_up <= 0.45:
            side = Side.SELL
            confidence = 1.0 - p_up
        else:
            side = Side.FLAT
            confidence = 0.5

        # Predicted path: +1, +2, +3 steps of expected move
        levels = [ret_hat, ret_hat * 1.6, ret_hat * 2.2]
        return confidence, side, levels


# ─────────────────────────────────────────────────────────────────────────────
# Direction score (F&O aware) + option trade plan
# ─────────────────────────────────────────────────────────────────────────────


def directional_score(features: FeatureVector, metrics: ChainMetrics, spot: float) -> tuple[float, list[str]]:
    """
    Composite score in [-1, +1].
    +1 = strong bullish → Buy CE (profit if market UP)
    -1 = strong bearish → Buy PE (profit if market DOWN)
    """
    reasons: list[str] = []
    parts: list[tuple[float, float]] = []  # (weight, signed contribution)

    # Trend: EMA9 vs EMA21
    if features.ema_spread > 0.0005:
        parts.append((0.22, 1.0))
        reasons.append("ema_uptrend")
    elif features.ema_spread < -0.0005:
        parts.append((0.22, -1.0))
        reasons.append("ema_downtrend")
    else:
        parts.append((0.22, 0.0))

    # Price vs VWAP
    if features.vwap_dist > 0.0008:
        parts.append((0.18, 1.0))
        reasons.append("above_vwap")
    elif features.vwap_dist < -0.0008:
        parts.append((0.18, -1.0))
        reasons.append("below_vwap")
    else:
        parts.append((0.18, features.vwap_dist / 0.002))

    # RSI momentum
    if features.rsi >= 58:
        parts.append((0.12, min(1.0, (features.rsi - 50) / 20)))
        reasons.append("rsi_bullish")
    elif features.rsi <= 42:
        parts.append((0.12, max(-1.0, (features.rsi - 50) / 20)))
        reasons.append("rsi_bearish")
    else:
        parts.append((0.12, (features.rsi - 50) / 25))

    # PCR: India F&O — elevated PCR often bullish (put writing / hedges)
    if metrics.pcr_oi >= 1.15:
        parts.append((0.16, 0.85))
        reasons.append("pcr_bullish")
    elif metrics.pcr_oi <= 0.75:
        parts.append((0.16, -0.85))
        reasons.append("pcr_bearish")
    else:
        parts.append((0.16, (metrics.pcr_oi - 1.0) * 1.5))

    # OI pressure: + call buildup often = resistance / short covering nuance;
    # we treat call OI build + price up as bullish continuation, put build + price down as bearish
    parts.append((0.12, float(np.clip(features.oi_pressure, -1, 1))))
    if features.oi_pressure > 0.25:
        reasons.append("call_oi_flow")
    elif features.oi_pressure < -0.25:
        reasons.append("put_oi_flow")

    # Max pain magnet
    if metrics.max_pain > 0 and spot > 0:
        dist = (spot - metrics.max_pain) / spot
        # If far above max pain → mild mean-reversion down; far below → up
        mp_signal = float(np.clip(-dist * 40, -1, 1))
        parts.append((0.10, mp_signal))
        if abs(dist) > 0.004:
            reasons.append("max_pain_pull")

    # Volume confirmation
    if features.volume_z >= 1.5:
        # amplify existing direction via small boost later
        parts.append((0.10, 0.35 if features.ema_spread >= 0 else -0.35))
        reasons.append("volume_surge")
    else:
        parts.append((0.10, 0.0))

    wsum = sum(w for w, _ in parts) or 1.0
    score = sum(w * s for w, s in parts) / wsum
    return float(np.clip(score, -1.0, 1.0)), reasons


def pick_atm_option(
    contracts: list[OptionContract],
    spot: float,
    option_type: OptionType,
) -> OptionContract | None:
    pool = [c for c in contracts if c.option_type == option_type]
    if not pool:
        return None
    return min(pool, key=lambda c: abs(c.strike - spot))


@dataclass
class RiskPlan:
    entry: float
    stop_loss: float
    target: float
    target_2: float
    target_3: float
    trailing_sl: float
    rr_ratio: float
    valid: bool
    reason: str


def compute_risk_plan(
    side: Side,
    spot: float,
    atr: float,
    settings: Settings,
    predicted_ret: float = 0.0,
) -> RiskPlan:
    if side == Side.FLAT or spot <= 0:
        return RiskPlan(spot, spot, spot, spot, spot, spot, 0.0, False, "flat/invalid")

    # Floor ATR so thin mock candles still produce meaningful levels
    atr = max(atr, spot * 0.0018)
    sl_dist = atr * settings.default_sl_atr_mult
    ml_move = abs(predicted_ret) * spot
    t1 = max(atr * settings.default_target_atr_mult, ml_move, sl_dist * settings.min_rr_ratio)
    t2 = max(atr * settings.target2_atr_mult, t1 * 1.4)
    t3 = max(atr * settings.target3_atr_mult, t2 * 1.25)

    if side == Side.BUY:
        entry = spot
        sl = spot - sl_dist
        target = spot + t1
        target_2 = spot + t2
        target_3 = spot + t3
        trail = spot - sl_dist * 0.65
    else:
        entry = spot
        sl = spot + sl_dist
        target = spot - t1
        target_2 = spot - t2
        target_3 = spot - t3
        trail = spot + sl_dist * 0.65

    risk = abs(entry - sl)
    reward = abs(target - entry)
    rr = reward / risk if risk > 0 else 0.0
    valid = rr >= settings.min_rr_ratio
    reason = "ok" if valid else f"RR {rr:.2f} < {settings.min_rr_ratio:.1f}"
    return RiskPlan(entry, sl, target, target_2, target_3, trail, rr, valid, reason)


def build_option_legs(
    side: Side,
    spot: float,
    contracts: list[OptionContract],
    settings: Settings,
) -> dict[str, Any]:
    """
    F&O mapping:
      BUY (market up)  → Buy CE  — profit jab market upar jaaye
      SELL (market down) → Buy PE — profit jab market niche jaaye
    """
    if side == Side.BUY:
        opt_type = OptionType.CE
        bias = "BULLISH"
        action = "BUY CE (Call) — market upar jaane pe profit"
    elif side == Side.SELL:
        opt_type = OptionType.PE
        bias = "BEARISH"
        action = "BUY PE (Put) — market niche jaane pe bhi profit"
    else:
        return {
            "option_type": None,
            "option_strike": None,
            "option_ltp": None,
            "option_entry": None,
            "option_sl": None,
            "option_target": None,
            "option_target_2": None,
            "action_text": "WAIT — clear setup nahi",
            "exit_text": "",
            "direction_bias": "NEUTRAL",
        }

    contract = pick_atm_option(contracts, spot, opt_type)
    if not contract:
        prem = max(spot * 0.004, 20.0)
        strike = round(spot / 50) * 50
    else:
        prem = max(contract.ask or contract.ltp, 1.0)
        strike = contract.strike

    entry = round(prem, 2)
    sl = round(max(entry * (1.0 - settings.option_sl_pct), 0.5), 2)
    t1 = round(entry * (1.0 + settings.option_tgt1_pct), 2)
    t2 = round(entry * (1.0 + settings.option_tgt2_pct), 2)

    exit_text = (
        f"Premium {entry:.1f} pe BUY → Stop Loss {sl:.1f} pe EXIT/CUT → "
        f"Target1 {t1:.1f} / Target2 {t2:.1f} pe BOOK PROFIT"
    )

    return {
        "option_type": opt_type,
        "option_strike": strike,
        "option_ltp": round(contract.ltp, 2) if contract else entry,
        "option_entry": entry,
        "option_sl": sl,
        "option_target": t1,
        "option_target_2": t2,
        "action_text": f"{action} | Strike {strike:.0f}",
        "exit_text": exit_text,
        "direction_bias": bias,
    }


def update_trailing_sl(
    side: Side,
    last_price: float,
    current_trail: float,
    atr: float,
) -> float:
    step = max(atr * 0.5, last_price * 0.0008)
    if side == Side.BUY:
        return max(current_trail, last_price - step)
    if side == Side.SELL:
        return min(current_trail, last_price + step)
    return current_trail


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────


class QuantEngine:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.model = ConfidenceModel(self.settings.ml_model_path)
        self._last_signal_ts: int = 0
        self._cooldown_sec: int = self.settings.signal_cooldown_sec
        self.active_signal: Signal | None = None
        self.latest_live_plan: dict[str, Any] | None = None

    def analyze_chain(
        self,
        contracts: list[OptionContract],
        spot: float,
        candles: list[Candle],
    ) -> tuple[list[OptionContract], ChainMetrics]:
        T = years_to_expiry(self.settings.expiry)
        enriched = enrich_chain_greeks(contracts, spot, self.settings.risk_free_rate, T)
        pcr_oi, pcr_vol = put_call_ratio(enriched)
        metrics = ChainMetrics(
            pcr_oi=round(pcr_oi, 4),
            pcr_volume=round(pcr_vol, 4),
            max_pain=max_pain(enriched),
            vwap=round(vwap_from_candles(candles), 2) if candles else round(spot, 2),
            spot=spot,
            atm_iv=round(atm_iv(enriched, spot), 4),
            oi_buildup_strikes=detect_oi_buildup(enriched, self.settings.oi_buildup_threshold_pct),
            volume_breakout=volume_breakout(candles, self.settings.volume_breakout_zscore),
        )
        return enriched, metrics

    def generate_signal(
        self,
        underlying: str,
        spot: float,
        candles: list[Candle],
        contracts: list[OptionContract],
        metrics: ChainMetrics,
    ) -> Signal | None:
        now = int(time.time())
        features = build_features(candles, metrics, contracts)
        rule_score, rule_reasons = directional_score(features, metrics, spot)
        ml_conf, ml_side, rets = self.model.predict(features)

        # Blend rule score with ML: rules dominate for F&O direction clarity
        ml_signed = (ml_conf if ml_side == Side.BUY else (-ml_conf if ml_side == Side.SELL else 0.0))
        score = float(np.clip(0.65 * rule_score + 0.35 * ml_signed, -1.0, 1.0))

        if score >= 0.18:
            side = Side.BUY
            confidence = min(0.97, 0.50 + abs(score) * 0.48)
        elif score <= -0.18:
            side = Side.SELL
            confidence = min(0.97, 0.50 + abs(score) * 0.48)
        else:
            side = Side.FLAT
            confidence = 0.5 - abs(score) * 0.2

        atr = _atr(candles)
        predicted_ret = rets[0] if rets else score * 0.0025
        # Align ML trajectory sign with decided side
        if side == Side.BUY:
            predicted_ret = abs(predicted_ret)
        elif side == Side.SELL:
            predicted_ret = -abs(predicted_ret)

        plan = compute_risk_plan(side, spot, atr, self.settings, predicted_ret)
        legs = build_option_legs(side, spot, contracts, self.settings)

        if metrics.volume_breakout and "volume_surge" not in rule_reasons:
            rule_reasons.append("volume_breakout")

        pred_levels = [
            round(plan.target, 2),
            round(plan.target_2, 2),
            round(plan.target_3, 2),
        ]

        signal = Signal(
            id=str(uuid.uuid4())[:8],
            timestamp=now,
            underlying=underlying,
            side=side,
            entry=round(plan.entry, 2),
            stop_loss=round(plan.stop_loss, 2),
            target=round(plan.target, 2),
            target_2=round(plan.target_2, 2),
            target_3=round(plan.target_3, 2),
            trailing_sl=round(plan.trailing_sl, 2),
            confidence=round(confidence, 4),
            rr_ratio=round(plan.rr_ratio, 3),
            reason=",".join(rule_reasons) or "score",
            predicted_levels=pred_levels,
            discarded=False,
            option_type=legs["option_type"],
            option_strike=legs["option_strike"],
            option_ltp=legs["option_ltp"],
            option_entry=legs["option_entry"],
            option_sl=legs["option_sl"],
            option_target=legs["option_target"],
            option_target_2=legs["option_target_2"],
            action_text=legs["action_text"],
            exit_text=legs["exit_text"],
            direction_bias=legs["direction_bias"],
            score=round(score, 4),
        )

        # Always refresh live plan for UI (even if discarded)
        if side == Side.FLAT:
            signal = signal.model_copy(
                update={"discarded": True, "discard_reason": "no_clear_edge"}
            )
        elif confidence < self.settings.confidence_threshold:
            signal = signal.model_copy(
                update={
                    "discarded": True,
                    "discard_reason": f"confidence<{self.settings.confidence_threshold}",
                }
            )
        elif not plan.valid:
            signal = signal.model_copy(update={"discarded": True, "discard_reason": plan.reason})

        self.latest_live_plan = self._plan_dict(signal, spot)

        if now - self._last_signal_ts < self._cooldown_sec:
            if self.active_signal and self.active_signal.side != Side.FLAT:
                trail = update_trailing_sl(
                    self.active_signal.side,
                    spot,
                    self.active_signal.trailing_sl or self.active_signal.stop_loss,
                    max(atr, spot * 0.0018),
                )
                self.active_signal = self.active_signal.model_copy(update={"trailing_sl": trail})
                self.latest_live_plan = self._plan_dict(self.active_signal, spot)
            return signal if signal.discarded else None

        if signal.discarded:
            return signal

        self._last_signal_ts = now
        self.active_signal = signal
        self.latest_live_plan = self._plan_dict(signal, spot)
        return signal

    def _plan_dict(self, signal: Signal, spot: float) -> dict[str, Any]:
        active = not signal.discarded and signal.side != Side.FLAT
        bias = signal.direction_bias or (
            "BULLISH" if signal.side == Side.BUY else "BEARISH" if signal.side == Side.SELL else "NEUTRAL"
        )
        # Hindi+English clear instruction card
        if signal.side == Side.BUY and active:
            headline = f"▲ MARKET UP bias — {signal.underlying} pe BUY CE"
            spot_line = (
                f"Spot {signal.entry:.1f} se BUY zone | "
                f"Stop Loss {signal.stop_loss:.1f} pe EXIT | "
                f"T1 {signal.target:.1f} → T2 {signal.target_2:.1f} → T3 {signal.target_3:.1f}"
            )
        elif signal.side == Side.SELL and active:
            headline = f"▼ MARKET DOWN bias — {signal.underlying} pe BUY PE (niche pe profit)"
            spot_line = (
                f"Spot {signal.entry:.1f} se SHORT/PE zone | "
                f"Stop Loss {signal.stop_loss:.1f} pe EXIT | "
                f"T1 {signal.target:.1f} → T2 {signal.target_2:.1f} → T3 {signal.target_3:.1f}"
            )
        else:
            headline = f"⏳ WAIT — {signal.underlying} pe abhi clear high-probability setup nahi"
            spot_line = f"Live spot {spot:.1f} | score {signal.score:.2f} | setup refine ho raha hai"

        return {
            "active": active,
            "confidence": signal.confidence,
            "side": signal.side.value,
            "direction_bias": bias,
            "score": signal.score,
            "headline": headline,
            "spot_line": spot_line,
            "action_text": signal.action_text,
            "exit_text": signal.exit_text,
            "entry": signal.entry,
            "stop_loss": signal.stop_loss,
            "target": signal.target,
            "target_2": signal.target_2,
            "target_3": signal.target_3,
            "trailing_sl": signal.trailing_sl,
            "predicted_levels": signal.predicted_levels,
            "rr_ratio": signal.rr_ratio,
            "option_type": signal.option_type.value if signal.option_type else None,
            "option_strike": signal.option_strike,
            "option_ltp": signal.option_ltp,
            "option_entry": signal.option_entry,
            "option_sl": signal.option_sl,
            "option_target": signal.option_target,
            "option_target_2": signal.option_target_2,
            "reason": signal.reason,
            "discarded": signal.discarded,
            "discard_reason": signal.discard_reason,
        }

    def snapshot_prediction(self, spot: float, signal: Signal | None) -> dict[str, Any]:
        src = None
        if signal and not signal.discarded and signal.side != Side.FLAT:
            src = signal
        elif self.active_signal and self.active_signal.side != Side.FLAT:
            src = self.active_signal
        elif signal:
            src = signal
        elif self.latest_live_plan:
            return self.latest_live_plan

        if not src:
            return {
                "active": False,
                "confidence": 0.0,
                "side": Side.FLAT.value,
                "direction_bias": "NEUTRAL",
                "headline": "Waiting for live data…",
                "spot_line": f"Spot {spot:.1f}" if spot else "",
                "entry": None,
                "stop_loss": None,
                "target": None,
                "target_2": None,
                "target_3": None,
                "trailing_sl": None,
                "predicted_levels": [],
                "option_type": None,
                "option_entry": None,
                "option_sl": None,
                "option_target": None,
            }
        plan = self._plan_dict(src, spot)
        self.latest_live_plan = plan
        return plan

