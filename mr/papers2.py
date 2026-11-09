"""Runde 2: weitere Strategien aus Forschungsarbeiten.

    python -m mr.papers2

Gleiche Daten, Kosten und Train/Test-Aufteilung wie mr/papers.py.

  noise      Zarattini, Aziz, Barbon (2024, SSRN/SFI): "Beat the Market" – Noise-Area-
             Ausbruch, Prüfung alle 30 Min., Trailing-Stop an der Bandgrenze, flat zum Schluss.
             Ohne VWAP-Stop (keine Volumendaten).
  orb        Zarattini, Aziz (2023, SSRN): Opening Range Breakout. Richtung des ersten
             Balkens (hier 15 statt 5 Minuten), Stop am Tief/Hoch des Balkens,
             Ziel 10R, sonst Ausstieg zum Schluss.
  dash_cash  Etula, Rinne, Suominen, Vaittinen (2020, RFS): Aktien long vom letzten
             Verkaufstag vor Monatsende (Abwicklungsfrist) bis T+3, Anleihen ab T-2.
  ranaldo    Ranaldo (2009, JBF): Heimatwährung fällt während der eigenen Handelszeit
             und steigt während der US-Handelszeit.
  btc_mom    Shen, Urquhart, Wang (2022, Financial Review): erste halbe Stunde des
             UTC-Tages sagt die letzte halbe Stunde voraus.
  gold_asien Gold steigt in asiatischen Handelsstunden und fällt im Westen
             (Donati, Jung 2019, Masterarbeit CBS, betreut von P. Whelan).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .fetch import load
from .instruments import INSTRUMENTS
from .papers import (BER, DAYS, NY, SPLIT, START, TKY, Asset, _net, at, summary,
                     trades)
from .regime import daily_adx_at, label
from .run import RES

SYD = "Australia/Sydney"


def trades_px(a: Asset, entry, exit_, pe, px, side) -> pd.DataFrame:
    """Trades mit vorgegebenen Ein-/Ausstiegspreisen (z. B. Stop-Füllungen)."""
    entry, exit_ = pd.DatetimeIndex(entry), pd.DatetimeIndex(exit_)
    entry = entry if entry.tz is not None else entry.tz_localize("UTC")
    exit_ = exit_ if exit_.tz is not None else exit_.tz_localize("UTC")
    pe, px, side = np.asarray(pe, float), np.asarray(px, float), np.asarray(side, float)
    return pd.DataFrame({"asset": a.name, "klasse": a.klasse, "inst": a.inst,
                         "entry": entry.tz_convert(None), "exit": exit_.tz_convert(None),
                         "side": side.astype(int), "gross": side * (px / pe - 1),
                         "ret": _net(a, pe, px, side),
                         "ret_pine": _net(a, pe, px, side, "pine"),
                         "ret_taker": _net(a, pe, px, side, "taker")})


def trading_days(a: Asset, hhmm: str, tz: str) -> pd.DatetimeIndex:
    t = at(DAYS, hhmm, tz)
    return DAYS[~np.isnan(a.price(t))]


# --------------------------------------------------------------------------- Noise Area
SESSIONS = {  # Asset: (Eröffnung, Schluss, Zeitzone)
    "usa500idxusd": ("09:30", "16:00", NY), "usatechidxusd": ("09:30", "16:00", NY),
    "deuidxeur": ("09:00", "17:30", BER), "eemususd": ("09:30", "16:00", NY),
    "tltususd": ("09:30", "16:00", NY),
}


def _grid(open_, close, step):
    o = pd.Timedelta(open_ + ":00")
    c = pd.Timedelta(close + ":00")
    return [o + pd.Timedelta(minutes=step * k) for k in range(int((c - o) / pd.Timedelta(minutes=step)) + 1)]


def s_noise(A, lookback=14):
    out = []
    for inst, (op, cl, tz) in SESSIONS.items():
        a = A[inst]
        days = trading_days(a, cl, tz)
        grid = _grid(op, cl, 30)                         # 30-Minuten-Raster inkl. Eröffnung/Schluss
        times = [at(days, f"{int(g.total_seconds()//3600):02d}:{int(g.total_seconds()%3600//60):02d}", tz)
                 for g in grid]
        P = np.column_stack([a.price(t) for t in times])  # Tage × Zeitpunkte
        O, C = P[:, 0], P[:, -1]
        prevC = np.r_[np.nan, C[:-1]]
        move = np.abs(P / O[:, None] - 1)
        sig = pd.DataFrame(move).rolling(lookback, min_periods=lookback).mean().shift(1).to_numpy()
        up = np.maximum(O, prevC)[:, None] * (1 + sig)
        lo = np.minimum(O, prevC)[:, None] * (1 - sig)
        rows = []
        for d in range(len(days)):
            if np.isnan(sig[d, 1:]).all() or np.isnan(O[d]) or np.isnan(prevC[d]):
                continue
            pos, e_t, e_p = 0, None, None
            for k in range(1, len(grid)):
                p = P[d, k]
                if np.isnan(p):
                    continue
                last = k == len(grid) - 1
                # Ausstieg: Kurs fällt zurück hinter die eigene Bandgrenze (Trailing-Stop) oder Schluss
                if pos == 1 and (last or p < up[d, k]):
                    rows.append((e_t, times[k][d], e_p, p, 1)); pos = 0
                elif pos == -1 and (last or p > lo[d, k]):
                    rows.append((e_t, times[k][d], e_p, p, -1)); pos = 0
                if last:
                    break
                if pos == 0 and p > up[d, k]:
                    pos, e_t, e_p = 1, times[k][d], p
                elif pos == 0 and p < lo[d, k]:
                    pos, e_t, e_p = -1, times[k][d], p
        if rows:
            r = pd.DataFrame(rows, columns=["e", "x", "pe", "px", "s"])
            out.append(trades_px(a, r.e, r.x, r.pe, r.px, r.s))
    return pd.concat(out)


# --------------------------------------------------------------------------- ORB
def s_orb(A, target_r=10.0):
    out = []
    for inst, (op, cl, tz) in SESSIONS.items():
        a = A[inst]
        raw = a.raw
        days = trading_days(a, cl, tz)
        t_open = at(days, op, tz)
        t_close = at(days, cl, tz)
        start_naive = t_open.tz_convert(None)
        hi, lo = raw["high"], raw["low"]
        o_px, c1_px = a.price(t_open), a.price(t_open + pd.Timedelta("15min"))
        h1 = hi.reindex(start_naive).to_numpy()
        l1 = lo.reindex(start_naive).to_numpy()
        rows = []
        for d in range(len(days)):
            o, c, h, l = o_px[d], c1_px[d], h1[d], l1[d]
            if np.isnan([o, c, h, l]).any() or abs(c / o - 1) < 1e-4:
                continue                                   # kein Balken oder Doji
            side = 1 if c > o else -1
            stop = l if side == 1 else h
            risk = abs(c - stop)
            if risk <= 0:
                continue
            target = c + side * target_r * risk
            seg = raw.loc[start_naive[d] + pd.Timedelta("15min"): t_close[d].tz_convert(None) - pd.Timedelta("15min")]
            px, xt = np.nan, None
            for ts, bar in zip(seg.index, seg.itertuples()):
                hit_s = bar.low <= stop if side == 1 else bar.high >= stop
                hit_t = bar.high >= target if side == 1 else bar.low <= target
                if hit_s:                                  # konservativ: Stop vor Ziel
                    px, xt = stop, ts + pd.Timedelta("15min"); break
                if hit_t:
                    px, xt = target, ts + pd.Timedelta("15min"); break
            if xt is None:
                px, xt = a.price(t_close[d:d + 1])[0], t_close[d].tz_convert(None)
            if np.isnan(px):
                continue
            rows.append(((t_open[d] + pd.Timedelta("15min")).tz_convert(None), xt, c, px, side))
        r = pd.DataFrame(rows, columns=["e", "x", "pe", "px", "s"])
        out.append(trades_px(a, r.e, r.x, r.pe, r.px, r.s))
    return pd.concat(out)


# --------------------------------------------------------------------------- Dash for Cash
def _month_end_trades(a, days, hhmm, tz, k_entry, k_exit_after=3):
    """Long vom Schluss T-k_entry bis Schluss T+k_exit_after (T = letzter Handelstag)."""
    s = pd.Series(np.arange(len(days)), index=days)
    last = s.groupby([days.year, days.month]).max().to_numpy()
    e_idx, x_idx = [], []
    for i in last:
        k = k_entry(days[i]) if callable(k_entry) else k_entry
        if i - k >= 0 and i + k_exit_after < len(days):
            e_idx.append(i - k); x_idx.append(i + k_exit_after)
    e = at(days[e_idx], hhmm, tz)
    x = at(days[x_idx], hhmm, tz)
    return trades(a, e, x, 1)


def s_dash_cash(A):
    ref = A["tltususd"]                                    # ETF-CFD: handelt nur an NYSE-Tagen
    us_days = trading_days(ref, "16:00", NY)
    # Letzter Verkaufstag für Bargeld am Monatsende: T-(Abwicklungstage+1);
    # US-Aktien T+2 bis 27.5.2024, danach T+1
    k_us = lambda d: 3 if d < pd.Timestamp("2024-05-28") else 2
    out = []
    for inst in ["usa500idxusd", "usatechidxusd", "eemususd"]:
        out.append(_month_end_trades(A[inst], us_days, "16:00", NY, k_us))
    for inst in ["tltususd", "iefususd"]:                  # Treasuries: T+1 -> Verkauf bis T-2
        out.append(_month_end_trades(A[inst], us_days, "16:00", NY, 2))
    dax = A["deuidxeur"]
    out.append(_month_end_trades(dax, trading_days(dax, "17:30", BER), "17:30", BER, 3))
    nik = A["jpnidxjpy"]
    out.append(_month_end_trades(nik, trading_days(nik, "15:00", TKY), "15:00", TKY, 3))
    return pd.concat(out)


# --------------------------------------------------------------------------- Ranaldo
RANALDO = {  # Paar: (USD-Richtung des Kurses, Heimat-Fenster, US-Fenster)
    "eurusd": (-1, ("08:00", "14:00", BER), ("11:00", "17:00", NY)),
    "gbpusd": (-1, ("08:00", "13:00", "Europe/London"), ("11:00", "17:00", NY)),
    "usdchf": (1, ("08:00", "14:00", BER), ("11:00", "17:00", NY)),
    "usdjpy": (1, ("09:00", "15:00", TKY), ("08:00", "16:00", NY)),
    "audusd": (-1, ("10:00", "16:00", SYD), ("08:00", "16:00", NY)),
}


def s_ranaldo(A):
    out = []
    for inst, (usd, (h0, h1, htz), (u0, u1, utz)) in RANALDO.items():
        a = A[inst]
        # Heimatwährung fällt in Heimat-Stunden -> USD long; steigt in US-Stunden -> USD short
        t = trades(a, at(DAYS, h0, htz), at(DAYS, h1, htz), usd); t["leg"] = "Heimat-Stunden"; out.append(t)
        t = trades(a, at(DAYS, u0, utz), at(DAYS, u1, utz), -usd); t["leg"] = "US-Stunden"; out.append(t)
    return pd.concat(out)


# --------------------------------------------------------------------------- BTC-Momentum
def s_btc_mom(A):
    a = A["btcusd"]
    r1 = a.price(at(DAYS, "00:30", "UTC")) / a.price(at(DAYS, "00:00", "UTC")) - 1
    return trades(a, at(DAYS, "23:30", "UTC"), at(DAYS + pd.Timedelta("1D"), "00:00", "UTC"),
                  np.sign(np.nan_to_num(r1)))


# --------------------------------------------------------------------------- Gold
def s_gold_asien(A):
    a = A["xauusd"]
    t1 = trades(a, at(DAYS, "00:00", "UTC"), at(DAYS, "07:00", "UTC"), 1); t1["leg"] = "Asien long"
    t2 = trades(a, at(DAYS, "13:00", "UTC"), at(DAYS, "20:00", "UTC"), -1); t2["leg"] = "USA short"
    return pd.concat([t1, t2])


STRATEGIES = {
    "noise": ("Noise-Area-Momentum (Zarattini et al. 2024)", s_noise),
    "orb": ("Opening Range Breakout 15 Min. (Zarattini & Aziz 2023)", s_orb),
    "dash_cash": ("Dash for Cash Monatsende (Etula et al. 2020)", s_dash_cash),
    "ranaldo": ("FX Heimat- vs. US-Stunden (Ranaldo 2009)", s_ranaldo),
    "btc_mom": ("Bitcoin Intraday-Momentum (Shen et al. 2022)", s_btc_mom),
    "gold_asien": ("Gold Asien long / USA short (Donati & Jung 2019)", s_gold_asien),
}


def run() -> pd.DataFrame:
    A = {i: Asset(i) for i in INSTRUMENTS if load(i) is not None}
    allt = []
    for key, (title, fn) in STRATEGIES.items():
        t = fn(A).reset_index(drop=True)
        t["strategie"] = key
        t = t[t.entry >= pd.Timestamp(START)]
        allt.append(t)
        print(f"{title:55s} {len(t):6d} Trades", flush=True)
    t = pd.concat(allt, ignore_index=True)
    t["periode"] = np.where(t.entry < pd.Timestamp(SPLIT), "train", "test")
    t["regime"] = None
    for inst, g in t.groupby("inst"):
        t.loc[g.index, "regime"] = label(pd.Series(daily_adx_at(A[inst].raw, g.entry), index=g.index)).to_numpy()
    return t


def main():
    t = run()
    (RES / "papers").mkdir(parents=True, exist_ok=True)
    t.to_parquet(RES / "papers" / "trades2.parquet", compression="zstd")
    s = t.groupby(["strategie", "periode"]).apply(summary).unstack("periode")
    print(s.round(5).to_string())


if __name__ == "__main__":
    main()
