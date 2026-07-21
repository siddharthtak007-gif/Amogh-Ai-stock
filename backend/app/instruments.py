"""Searchable F&O instrument universe (indices + liquid stocks)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    segment: str  # INDEX | STOCK
    base_spot: float
    strike_step: float
    lot_size: int
    exchange: str = "NSE"


# Representative mock base prices — replace with live LTP when broker is wired
INSTRUMENTS: list[Instrument] = [
    Instrument("NIFTY", "Nifty 50", "INDEX", 24_500.0, 50.0, 25),
    Instrument("BANKNIFTY", "Bank Nifty", "INDEX", 52_000.0, 100.0, 15),
    Instrument("FINNIFTY", "Fin Nifty", "INDEX", 23_200.0, 50.0, 25),
    Instrument("MIDCPNIFTY", "Nifty Midcap Select", "INDEX", 12_800.0, 25.0, 50),
    Instrument("SENSEX", "BSE Sensex", "INDEX", 80_500.0, 100.0, 10),
    Instrument("RELIANCE", "Reliance Industries", "STOCK", 2_980.0, 20.0, 250),
    Instrument("TCS", "Tata Consultancy Services", "STOCK", 4_150.0, 20.0, 150),
    Instrument("INFY", "Infosys", "STOCK", 1_890.0, 10.0, 400),
    Instrument("HDFCBANK", "HDFC Bank", "STOCK", 1_720.0, 10.0, 550),
    Instrument("ICICIBANK", "ICICI Bank", "STOCK", 1_280.0, 10.0, 700),
    Instrument("SBIN", "State Bank of India", "STOCK", 820.0, 5.0, 750),
    Instrument("BHARTIARTL", "Bharti Airtel", "STOCK", 1_650.0, 10.0, 475),
    Instrument("ITC", "ITC Limited", "STOCK", 470.0, 5.0, 1_600),
    Instrument("LT", "Larsen & Toubro", "STOCK", 3_620.0, 20.0, 150),
    Instrument("AXISBANK", "Axis Bank", "STOCK", 1_150.0, 10.0, 625),
    Instrument("KOTAKBANK", "Kotak Mahindra Bank", "STOCK", 1_980.0, 10.0, 400),
    Instrument("BAJFINANCE", "Bajaj Finance", "STOCK", 7_250.0, 50.0, 125),
    Instrument("MARUTI", "Maruti Suzuki", "STOCK", 12_400.0, 100.0, 50),
    Instrument("TATAMOTORS", "Tata Motors", "STOCK", 980.0, 5.0, 550),
    Instrument("WIPRO", "Wipro", "STOCK", 290.0, 2.5, 3_000),
    Instrument("HCLTECH", "HCL Technologies", "STOCK", 1_860.0, 10.0, 350),
    Instrument("ASIANPAINT", "Asian Paints", "STOCK", 2_450.0, 20.0, 200),
    Instrument("SUNPHARMA", "Sun Pharmaceutical", "STOCK", 1_780.0, 10.0, 350),
    Instrument("TITAN", "Titan Company", "STOCK", 3_450.0, 20.0, 175),
    Instrument("ULTRACEMCO", "UltraTech Cement", "STOCK", 11_200.0, 100.0, 50),
]

_BY_SYMBOL = {i.symbol.upper(): i for i in INSTRUMENTS}


def get_instrument(symbol: str) -> Instrument | None:
    return _BY_SYMBOL.get(symbol.strip().upper())


def search_instruments(query: str = "", limit: int = 25) -> list[Instrument]:
    q = query.strip().upper()
    if not q:
        return INSTRUMENTS[:limit]
    hits: list[Instrument] = []
    for inst in INSTRUMENTS:
        hay = f"{inst.symbol} {inst.name}".upper()
        if q in hay or inst.symbol.startswith(q):
            hits.append(inst)
        if len(hits) >= limit:
            break
    return hits


def list_all() -> list[dict]:
    return [
        {
            "symbol": i.symbol,
            "name": i.name,
            "segment": i.segment,
            "base_spot": i.base_spot,
            "strike_step": i.strike_step,
            "lot_size": i.lot_size,
            "exchange": i.exchange,
        }
        for i in INSTRUMENTS
    ]
