"""Backtest über alle Instrumente und Timeframes.

    python -m mr.run            # alle Instrumente mit Daten
    python -m mr.run eurusd     # nur einzelne

Schreibt results/summary.csv, results/summary.md und results/trades/*.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import Params, backtest, stats
from .fetch import DATA, load
from .instruments import INSTRUMENTS, SPLITS

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TIMEFRAMES = {"15m": None, "1h": "1h", "4h": "4h"}
AGG = {"open": "first", "high": "max", "low": "min", "close": "last"}


def resample(df: pd.DataFrame, rule: str | None) -> pd.DataFrame:
    if rule is None:
        return df
    return df.resample(rule, origin="epoch", label="left", closed="left").agg(AGG).dropna()


def pct(x, d=1):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f} %"


def num(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return "∞" if np.isinf(x) else f"{x:.{d}f}"


def markdown(s: pd.DataFrame, p: Params) -> str:
    out = ["# Ergebnisse OU Mean Reversion\n",
           f"Parameter: EMA/Sigma {p.lenMu}/{p.lenSig}, Entry-Z {p.zEntry}, Ziel {p.zTarget} σ, "
           f"Stop {p.stopDist} σ, Flat-Filter {'an' if p.useFlat else 'aus'} "
           f"(max. Slope {p.maxSlope}), Zeit-Stop {p.maxBars} Balken, "
           f"Größe {p.pct:.0%} vom Kapital, Kommission {p.comm:.2%} je Seite, "
           f"Slippage {p.slip_ticks} Ticks. Daten: Dukascopy (Bid).\n",
           "Ø Trade, Gewinn und Verlust beziehen sich auf den einzelnen Trade "
           "(unabhängig von der Positionsgröße). Rendite, CAGR und Max DD beziehen "
           "sich aufs Gesamtkapital bei 2 % Einsatz je Trade.\n"]
    for tf in TIMEFRAMES:
        t = s[s.tf == tf]
        if t.empty:
            continue
        out.append(f"\n## {tf}\n")
        out.append("| Asset | Klasse | Zeitraum | Trades | Treffer | Ø Trade | Ø Gewinn | Ø Verlust "
                   "| Profit Factor | Ø Long | Ø Short | Ziel/Stop/Zeit | CAGR | Max DD | B&H CAGR |")
        out.append("|" + "---|" * 15)
        for _, r in t.iterrows():
            out.append(
                f"| {r['name']} | {r.klasse} | {r.von[:4]}–{r.bis[:4]} | {int(r.trades)} | "
                f"{pct(r.get('trefferquote'), 0)} | {pct(r.get('avg_trade'), 3)} | "
                f"{pct(r.get('avg_gewinn'), 2)} | {pct(r.get('avg_verlust'), 2)} | "
                f"{num(r.get('profit_factor'))} | {pct(r.get('avg_long'), 3)} | "
                f"{pct(r.get('avg_short'), 3)} | "
                f"{num(r.get('exit_ziel'), 0)}/{num(r.get('exit_stop'), 0)}/{num(r.get('exit_zeit'), 0)} | "
                f"{pct(r.cagr, 2)} | {pct(r.max_dd, 2)} | {pct(r.bh_cagr, 1)} |")
    return "\n".join(out) + "\n"


def main(only: list[str]) -> None:
    p = Params()
    rows = []
    (RES / "trades").mkdir(parents=True, exist_ok=True)
    for inst, (name, klasse, tick, _) in INSTRUMENTS.items():
        if only and inst not in only:
            continue
        raw = load(inst)
        if raw is None or raw.empty:
            print(f"{inst}: keine Daten, übersprungen")
            continue
        for day, factor in SPLITS.get(inst, []):
            raw.loc[raw.index < day] *= factor
        for tf, rule in TIMEFRAMES.items():
            df = resample(raw, rule)
            eq, tr = backtest(df, p, tick)
            st = stats(eq, tr, df["close"])
            rows.append({"instrument": inst, "name": name, "klasse": klasse, "tf": tf, **st})
            tr.to_csv(RES / "trades" / f"{inst}_{tf}.csv", index=False)
            print(f"{name:28s} {tf:>3s}: {st['trades']:5d} Trades, "
                  f"PF {st.get('profit_factor', float('nan')):.2f}, "
                  f"Ø {st.get('avg_trade', float('nan')) * 100:.3f} %")
    if not rows:
        raise SystemExit("keine Daten vorhanden – erst den Daten-Workflow laufen lassen")
    s = pd.DataFrame(rows)
    if only and (RES / "summary.csv").exists():   # Teil-Lauf in bestehende Tabelle mischen
        old = pd.read_csv(RES / "summary.csv")
        s = pd.concat([old[~old.instrument.isin(only)], s])
    order = {k: i for i, k in enumerate(INSTRUMENTS)}
    s = s.sort_values(["tf", "instrument"], key=lambda c: c.map(order) if c.name == "instrument"
                      else c.map(list(TIMEFRAMES).index))
    s.round(6).to_csv(RES / "summary.csv", index=False)
    (RES / "summary.md").write_text(markdown(s, p))


if __name__ == "__main__":
    main(sys.argv[1:])
