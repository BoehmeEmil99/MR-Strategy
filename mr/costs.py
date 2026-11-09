"""Handelskosten je Instrument.

Standard sind realistische Kosten je Seite in Basispunkten (1 bp = 0,01 %), inklusive
halbem Spread und Kommission, für die günstigste übliche Umsetzung:
Index-, Anleihe- und Rohstoff-Futures bzw. ETFs über Interactive Brokers, Devisen spot
über Interactive Brokers, Bitcoin als Perpetual-Future bei Binance mit Limit-Orders (Maker).

Mit der Umgebungsvariable MR_KOSTEN=pine gelten stattdessen die Kosten aus dem
Pine-Code: 0,02 % Kommission je Seite plus 2 Ticks Slippage.

Die Werte sind Schätzungen (Stand Nov. 2026), Herleitung in results/kosten.md.
"""
from __future__ import annotations

import os

MODE = os.environ.get("MR_KOSTEN", "real").lower()

REAL_BP = {
    # Aktien (Futures ES, NQ, FDAX, Nikkei; EEM als ETF)
    "usa500idxusd": 0.5, "usatechidxusd": 0.5, "deuidxeur": 0.5, "jpnidxjpy": 0.8,
    "eemususd": 1.0,
    # Anleihen (TLT/IEF als ETF, Bund-Future)
    "tltususd": 0.6, "iefususd": 0.6, "bundtreur": 0.5,
    # Credit (JNK als ETF)
    "jnkususd": 0.6,
    # Rohstoffe (Gold-Future GC, Öl-Future CL)
    "xauusd": 0.3, "lightcmdusd": 0.8,
    # Devisen (IBKR spot: 0,2 bp Kommission + halber Spread; Dollar-Index-Future DX)
    "eurusd": 0.3, "usdjpy": 0.3, "gbpusd": 0.3, "usdchf": 0.35, "audusd": 0.35,
    "usdcad": 0.35, "dollaridxusd": 0.4,
    # Krypto (Binance USDⓈ-M Perp, Maker 0,02 %)
    "btcusd": 2.0,
}
BTC_TAKER_BP = 5.0           # Binance Taker 0,05 % (für Vergleich ausgewiesen)
PINE_COMM, PINE_SLIP_TICKS = 0.0002, 2


def cost(inst: str, tick: float, mode: str | None = None) -> tuple[float, float]:
    """(Kommission als Anteil je Seite, Slippage als Preisdifferenz je Seite)."""
    if (mode or MODE) == "pine":
        return PINE_COMM, PINE_SLIP_TICKS * tick
    return REAL_BP[inst] / 1e4, 0.0


def describe(mode: str | None = None) -> str:
    if (mode or MODE) == "pine":
        return "Kosten wie im Pine-Code: 0,02 % Kommission je Seite plus 2 Ticks Slippage"
    return ("realistische Kosten je Instrument (0,3–1,0 bp je Seite für Futures, ETFs und Devisen, "
            "2 bp für Bitcoin mit Limit-Orders; siehe results/kosten.md)")
