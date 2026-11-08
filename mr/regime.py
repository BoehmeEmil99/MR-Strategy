"""Marktregime: trendend vs. konsolidierend.

Maß ist der Tages-ADX(14) nach Wilder (wie ta.dmi in Pine) des letzten
abgeschlossenen Tages vor dem Einstieg – also nur mit Informationen, die
beim Einstieg bekannt sind. Bewusst nicht der ADX auf dem Trade-Timeframe:
der misst beim Einstieg genau die Bewegung, gegen die die Strategie handelt,
und ist deshalb fast immer hoch.

    ADX >= 25  -> Trend
    ADX <  20  -> Konsolidierung
    dazwischen -> Übergang
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ADX_LEN = 14
TREND = 25.0
RANGE = 20.0
LABELS = ["Konsolidierung", "Übergang", "Trend"]


def _rma(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int = ADX_LEN) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up, down = h.diff(), -l.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = _rma(tr, n)
    plus = 100 * _rma(plus_dm, n) / atr
    minus = 100 * _rma(minus_dm, n) / atr
    dx = 100 * (plus - minus).abs() / (plus + minus).replace(0, np.nan)
    out = _rma(dx, n)
    out.iloc[: 2 * n] = np.nan
    return out


def label(a: pd.Series) -> pd.Series:
    return pd.Series(np.select([a >= TREND, a < RANGE], ["Trend", "Konsolidierung"], "Übergang"),
                     index=a.index).where(a.notna())


def daily_adx_at(m15: pd.DataFrame, when: pd.Series) -> np.ndarray:
    """Tages-ADX des Vortags für jeden Zeitpunkt in `when`."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    d = m15.resample("1D").agg(agg)
    d = d[m15["close"].resample("1D").count() >= 20].dropna()   # Rumpftage (z. B. Sonntag) raus
    a = adx(d).shift(1)                                          # nur abgeschlossene Tage
    return a.reindex(pd.DatetimeIndex(when).normalize(), method="ffill").to_numpy()
