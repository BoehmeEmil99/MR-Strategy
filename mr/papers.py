"""Backtest von Intraday-Strategien aus Forschungsarbeiten.

    python -m mr.papers

Alle Strategien sind über Uhrzeiten definiert und werden auf den
15-Minuten-Daten ausgeführt: Einstieg und Ausstieg zum Schlusskurs des
15-Minuten-Balkens, der zur jeweiligen Uhrzeit endet. Kosten wie beim
OU-Backtest: 0,02 % Kommission je Seite plus 2 Ticks Slippage je Seite.
Train = Einstiege 2020–2023, Test = Einstiege ab 2024.

Strategien (Quellen in results/papers.md):
  gao        Gao, Han, Li, Zhou (2018, JFE): Rendite Vortagesschluss → 10:00 ET
             sagt Richtung der letzten halben Stunde (15:30–16:00 ET) voraus.
  baltussen  Baltussen, Da, Lammers, Martens (2021, JFE): Rendite Vortagesschluss →
             30 Min. vor Schluss sagt die letzten 30 Min. voraus, alle Asset-Klassen.
  drift      Boyarchenko, Larsen, Whelan (2023, RFS): S&P 500/Nasdaq long 02:00–03:00 ET.
  drift_neg  wie drift, aber nur nach einem negativen US-Handelstag.
  fx_fix     Krohn, Mueller, Whelan (2024, JF): USD long vor den Fixings,
             USD short danach (Tokio- und Europa-Fenster).
  fomc       Lucca, Moench (2015, JF): Aktien long in den 24 h vor dem
             FOMC-Entscheid (13:45 ET Vortag → 13:45 ET).
  periodik   Heston, Korajczyk, Sadka (2010, JF), als Zeitreihen-Variante:
             jeden Tag long in der Stunde mit der besten, short in der mit der
             schlechtesten Ø-Rendite derselben Stunde der letzten 40 Tage.
  btc_abend  Padyšák, Vojtko (2022, SSRN): Bitcoin long 21:00–23:00 UTC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import Params
from .fetch import load
from .instruments import INSTRUMENTS, SPLITS
from .regime import daily_adx_at, label
from .run import RES

START, SPLIT, END = "2020-01-01", "2024-01-01", "2026-12-31"
COST = Params()                       # comm 0,02 % je Seite, 2 Ticks Slippage
TOL = pd.Timedelta("30min")           # max. Alter des letzten Kurses

NY, LON, BER, TKY = "America/New_York", "Europe/London", "Europe/Berlin", "Asia/Tokyo"

US_SESSION = ["usa500idxusd", "usatechidxusd", "eemususd", "tltususd", "iefususd", "jnkususd"]
EQUITY = ["usa500idxusd", "usatechidxusd", "deuidxeur", "jpnidxjpy", "eemususd"]
FX_USD = {  # +1: Kurs steigt, wenn der USD steigt
    "eurusd": -1, "gbpusd": -1, "audusd": -1, "usdjpy": 1, "usdchf": 1, "usdcad": 1, "dollaridxusd": 1,
}
# Börsenschluss je Asset für Baltussen et al. (Ortszeit)
CLOSE = {
    "usa500idxusd": ("16:00", NY), "usatechidxusd": ("16:00", NY), "eemususd": ("16:00", NY),
    "tltususd": ("16:00", NY), "iefususd": ("16:00", NY), "jnkususd": ("16:00", NY),
    "deuidxeur": ("17:30", BER), "jpnidxjpy": ("15:00", TKY), "bundtreur": ("17:15", BER),
    "xauusd": ("13:30", NY), "lightcmdusd": ("14:30", NY),
    "dollaridxusd": ("15:00", NY), "eurusd": ("15:00", NY), "usdjpy": ("15:00", NY),
    "gbpusd": ("15:00", NY), "usdchf": ("15:00", NY), "audusd": ("15:00", NY), "usdcad": ("15:00", NY),
    "btcusd": ("00:00", "UTC"),
}
# Geplante FOMC-Entscheide (2. Sitzungstag, 14:00 ET), März 2020 entfiel (Notfallsitzungen)
FOMC = """2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15
2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14
2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18
2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28""".split()

DAYS = pd.date_range(START, END, freq="D")


# --------------------------------------------------------------------------- Daten
class Asset:
    def __init__(self, inst: str):
        raw = load(inst)
        for day, f in SPLITS.get(inst, []):
            raw.loc[raw.index < day] *= f
        self.inst, self.raw = inst, raw
        self.name, self.klasse, self.tick = INSTRUMENTS[inst][:3]
        end = raw.index + pd.Timedelta("15min")          # Balken-Ende = Zeitpunkt des Schlusskurses
        self.t = end.tz_localize("UTC").as_unit("ns").asi8
        self.c = raw["close"].to_numpy()

    def price(self, when: pd.DatetimeIndex) -> np.ndarray:
        """Letzter Schlusskurs zum Zeitpunkt `when` (UTC), NaN wenn älter als TOL."""
        w = when.tz_convert("UTC").as_unit("ns").asi8
        i = np.searchsorted(self.t, w, side="right") - 1
        ok = (i >= 0) & (w - self.t[np.clip(i, 0, None)] <= TOL.value)
        out = np.full(len(w), np.nan)
        out[ok] = self.c[i[ok]]
        return out


def at(days: pd.DatetimeIndex, hhmm: str, tz: str) -> pd.DatetimeIndex:
    """Uhrzeit `hhmm` in Zeitzone `tz` an jedem Tag, als UTC."""
    h, m = map(int, hhmm.split(":"))
    loc = (days + pd.Timedelta(hours=h, minutes=m)).tz_localize(
        tz, ambiguous=False, nonexistent="shift_forward")
    return loc.tz_convert("UTC")


def trades(a: Asset, entry: pd.DatetimeIndex, exit_: pd.DatetimeIndex, side) -> pd.DataFrame:
    side = np.broadcast_to(np.asarray(side, float), (len(entry),)).copy()
    pe, px = a.price(entry), a.price(exit_)
    ok = ~np.isnan(pe) & ~np.isnan(px) & (side != 0) & (exit_ > entry)
    pe, px, side = pe[ok], px[ok], side[ok]
    slip = COST.slip_ticks * a.tick
    e, x = pe + side * slip, px - side * slip
    gross = side * (px / pe - 1)
    net = side * (x / e - 1) - COST.comm * (1 + x / e)
    return pd.DataFrame({"asset": a.name, "klasse": a.klasse, "inst": a.inst,
                         "entry": entry[ok].tz_convert(None), "exit": exit_[ok].tz_convert(None),
                         "side": side.astype(int), "gross": gross, "ret": net})


def daily_close(a: Asset, hhmm: str, tz: str) -> pd.Series:
    """Schlusskurs je Handelstag (nur Tage mit Kurs), Index = Schlusszeit in UTC."""
    t = at(DAYS, hhmm, tz)
    return pd.Series(a.price(t), index=t).dropna()


# --------------------------------------------------------------------------- Strategien
def s_gao(A):
    out = []
    for inst in US_SESSION:
        a = A[inst]
        close = daily_close(a, "16:00", NY)
        prev = close.shift(1)                                    # letzter vorheriger Handelstag
        t10, t1530, t16 = at(DAYS, "10:00", NY), at(DAYS, "15:30", NY), at(DAYS, "16:00", NY)
        p_prev = prev.reindex(t16).to_numpy()                    # Schluss vor diesem Tag
        r1 = a.price(t10) / p_prev - 1
        out.append(trades(a, t1530, t16, np.sign(np.nan_to_num(r1))))
    return pd.concat(out)


def s_baltussen(A):
    out = []
    for inst, (hhmm, tz) in CLOSE.items():
        a = A[inst]
        tc = at(DAYS, hhmm, tz)
        t30 = tc - pd.Timedelta("30min")
        close = pd.Series(a.price(tc), index=tc).dropna()
        p_prev = close.shift(1).reindex(tc).to_numpy()
        r = a.price(t30) / p_prev - 1
        out.append(trades(a, t30, tc, np.sign(np.nan_to_num(r))))
    return pd.concat(out)


def s_drift(A, only_after_down=False):
    out = []
    for inst in ["usa500idxusd", "usatechidxusd"]:
        a = A[inst]
        t2, t3 = at(DAYS, "02:00", NY), at(DAYS, "03:00", NY)
        side = np.ones(len(DAYS))
        if only_after_down:
            o = pd.Series(a.price(at(DAYS, "09:30", NY)), index=DAYS)
            c = pd.Series(a.price(at(DAYS, "16:00", NY)), index=DAYS)
            day_ret = (c / o - 1).dropna()
            # letzter US-Handelstag vor dem Morgen (über Wochenende hinweg)
            prev = day_ret.reindex(DAYS - pd.Timedelta("1D"), method="ffill").to_numpy()
            side = np.where(prev < 0, 1.0, 0.0)
        out.append(trades(a, t2, t3, side))
    return pd.concat(out)


def s_fx_fix(A):
    out = []
    for inst, usd in FX_USD.items():
        a = A[inst]
        t17 = at(DAYS, "17:00", NY)
        tky = at(DAYS + pd.Timedelta("1D"), "10:00", TKY)        # Tokio-Fix 9:55 am Folgetag
        t02 = at(DAYS + pd.Timedelta("1D"), "02:00", NY)
        e02, e0815 = at(DAYS, "02:00", NY), at(DAYS, "08:15", NY)
        l11, l17 = at(DAYS, "11:00", NY), at(DAYS, "17:00", NY)
        legs = [(t17, tky, usd, "Tokio vor Fix"), (tky, t02, -usd, "Tokio nach Fix"),
                (e02, e0815, usd, "Europa vor EZB-Fix"), (l11, l17, -usd, "nach London-Fix")]
        for e, x, s, name in legs:
            t = trades(a, e, x, s)
            t["leg"] = name
            out.append(t)
    return pd.concat(out)


def s_fomc(A):
    ann = pd.DatetimeIndex(pd.to_datetime(FOMC))
    prev_day = ann - pd.offsets.BDay(1)
    out = []
    for inst in EQUITY:
        a = A[inst]
        out.append(trades(a, at(prev_day, "13:45", NY), at(ann, "13:45", NY), 1))
    return pd.concat(out)


def s_periodik(A, lookback=40):
    out = []
    for inst, a in A.items():
        h = a.raw["close"].resample("1h").last().dropna()
        r = h.pct_change()
        r = r[r.index >= pd.Timestamp(START) - pd.Timedelta(days=lookback * 2)]
        tab = r.groupby([r.index.normalize(), r.index.hour]).first().unstack()   # Tage × Stunden
        cnt = tab.notna().rolling(lookback, min_periods=1).sum().shift(1)
        mean = tab.rolling(lookback, min_periods=lookback // 2).mean().shift(1)
        mean = mean.where(cnt >= lookback // 2)
        mean = mean[mean.index >= pd.Timestamp(START)]
        valid = mean.notna().sum(axis=1) >= 4
        mean = mean[valid]
        if mean.empty:
            continue
        best, worst = mean.idxmax(axis=1), mean.idxmin(axis=1)
        d = mean.index.tz_localize("UTC")
        for hours, side in ((best, 1), (worst, -1)):
            hh = pd.to_timedelta(hours.to_numpy(), unit="h")
            e = d + hh                                            # Stunde h beginnt um h:00
            out.append(trades(a, e, e + pd.Timedelta("1h"), side))
    return pd.concat(out)


def s_btc_abend(A):
    a = A["btcusd"]
    return trades(a, at(DAYS, "21:00", "UTC"), at(DAYS, "23:00", "UTC"), 1)


STRATEGIES = {
    "gao": ("Intraday-Momentum (Gao et al. 2018)", s_gao),
    "baltussen": ("Intraday-Momentum alle Klassen (Baltussen et al. 2021)", s_baltussen),
    "drift": ("Overnight Drift 2–3 Uhr ET (Boyarchenko et al. 2023)", s_drift),
    "drift_neg": ("Overnight Drift nur nach Minus-Tag", lambda A: s_drift(A, True)),
    "fx_fix": ("FX-Fixing-Reversal (Krohn et al. 2024)", s_fx_fix),
    "fomc": ("Pre-FOMC-Drift (Lucca & Moench 2015)", s_fomc),
    "periodik": ("Intraday-Periodizität (Heston et al. 2010)", s_periodik),
    "btc_abend": ("Bitcoin 21–23 Uhr UTC (Padyšák & Vojtko 2022)", s_btc_abend),
}


# --------------------------------------------------------------------------- Auswertung
def summary(t: pd.DataFrame) -> pd.Series:
    n = len(t)
    if n == 0:
        return pd.Series({"n": 0})
    r, g = t.ret, t.gross
    sd = r.std() if n > 1 else np.nan
    return pd.Series({
        "n": n,
        "brutto": g.mean(),
        "netto": r.mean(),
        "t_netto": r.mean() / sd * np.sqrt(n) if sd and sd > 0 else np.nan,
        "t_brutto": g.mean() / g.std() * np.sqrt(n) if n > 1 and g.std() > 0 else np.nan,
        "treffer": (r > 0).mean(),
        "pf": r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.inf,
        "breakeven_kosten_je_seite": g.mean() / 2,
    })


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
    # Regime (Tages-ADX des Vortags) je Asset
    t["regime"] = None
    for inst, g in t.groupby("inst"):
        adx = daily_adx_at(A[inst].raw, g.entry)
        t.loc[g.index, "regime"] = label(pd.Series(adx, index=g.index)).to_numpy()
    if "leg" not in t:
        t["leg"] = None
    return t


def main():
    t = run()
    (RES / "papers").mkdir(parents=True, exist_ok=True)
    t.to_parquet(RES / "papers" / "trades.parquet", compression="zstd")
    s = t.groupby(["strategie", "periode"]).apply(summary).unstack("periode")
    print(s.round(5).to_string())


if __name__ == "__main__":
    main()
