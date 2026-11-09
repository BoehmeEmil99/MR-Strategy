"""Backtest über alle Instrumente und Timeframes.

    python -m mr.run            # alle Instrumente mit Daten
    python -m mr.run eurusd     # nur einzelne

Schreibt results/summary.*, results/regime.* und results/trades/*.csv.
Gezählt werden Trades mit Einstieg ab START; die Balken davor dienen nur
dem Einschwingen von EMA, Sigma und ADX.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dataclasses import replace

from .costs import cost, describe
from .engine import Params, backtest, stats
from .fetch import DATA, load
from .instruments import INSTRUMENTS, SPLITS
from .regime import LABELS, RANGE, TREND, daily_adx_at, label

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
TIMEFRAMES = {"15m": None, "1h": "1h", "4h": "4h"}
START = "2020-01-01"     # Backtest-Zeitraum: ab hier bis heute
WARMUP = 1000            # Balken vor START zum Einschwingen der Indikatoren
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
           f"Größe {p.pct:.0%} vom Kapital, {describe()}. Daten: Dukascopy (Bid).\n",
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


def regime_stats(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    w, lo = t.ret[t.ret > 0], t.ret[t.ret <= 0]
    return {
        "trades": len(t),
        "trefferquote": (t.ret > 0).mean(),
        "avg_trade": t.ret.mean(),
        "profit_factor": (w.sum() / -lo.sum()) if lo.sum() < 0 else np.inf,
        "avg_long": t.ret[t.side > 0].mean(),
        "avg_short": t.ret[t.side < 0].mean(),
        "anteil_stop": (t.why == "stop").mean(),
        "summe": t.ret.sum(),
    }


def _pool(g: pd.DataFrame) -> pd.Series:
    """Fasst Regime-Zeilen mehrerer Assets zusammen (gewichtet nach Trades)."""
    n = g.trades.sum()
    if n == 0:
        return pd.Series({"trades": 0})
    wavg = lambda c: (g[c] * g.trades).sum() / n
    return pd.Series({"trades": n, "trefferquote": wavg("trefferquote"),
                      "avg_trade": g.summe.sum() / n, "anteil_stop": wavg("anteil_stop"),
                      "assets_positiv": int((g.avg_trade > 0).sum()), "assets": int((g.trades > 0).sum())})


def regime_markdown(r: pd.DataFrame) -> str:
    out = [f"# Trend vs. Konsolidierung (ab {START})\n",
           f"Regime beim Einstieg nach Tages-ADX(14) des Vortags: "
           f"Trend ab {TREND:.0f}, Konsolidierung unter {RANGE:.0f}, dazwischen Übergang. "
           "Ø Trade = Netto-Rendite je Trade nach Kosten.\n",
           "\n## Alle Assets zusammen\n",
           "| Timeframe | Regime | Trades | Treffer | Ø Trade | Anteil Stop | Assets mit Ø > 0 |",
           "|---|---|---|---|---|---|---|"]
    for tf in TIMEFRAMES:
        for rg in LABELS:
            g = _pool(r[(r.tf == tf) & (r.regime == rg)])
            if g.trades == 0:
                continue
            out.append(f"| {tf} | {rg} | {int(g.trades)} | {pct(g.trefferquote, 0)} | "
                       f"{pct(g.avg_trade, 3)} | {pct(g.anteil_stop, 0)} | "
                       f"{int(g.assets_positiv)} von {int(g.assets)} |")
    out += ["\n## Nach Asset-Klasse\n",
            "| Timeframe | Klasse | Konsolidierung Ø | Übergang Ø | Trend Ø | Trades K/Ü/T |",
            "|---|---|---|---|---|---|"]
    for tf in TIMEFRAMES:
        for kl in dict.fromkeys(r.klasse):
            cells, ns = [], []
            for rg in LABELS:
                g = _pool(r[(r.tf == tf) & (r.klasse == kl) & (r.regime == rg)])
                cells.append(pct(g.get("avg_trade"), 3) if g.trades else "–")
                ns.append(str(int(g.trades)))
            out.append(f"| {tf} | {kl} | " + " | ".join(cells) + f" | {'/'.join(ns)} |")
    for tf in TIMEFRAMES:
        out += [f"\n## {tf} je Asset\n",
                "| Asset | Konsolidierung: Trades · Treffer · Ø · PF | Trend: Trades · Treffer · Ø · PF |",
                "|---|---|---|"]
        for name in dict.fromkeys(r.name):
            cells = []
            for rg in ["Konsolidierung", "Trend"]:
                x = r[(r.tf == tf) & (r.name == name) & (r.regime == rg)]
                if x.empty or x.trades.iloc[0] == 0:
                    cells.append("–")
                    continue
                x = x.iloc[0]
                cells.append(f"{int(x.trades)} · {pct(x.trefferquote, 0)} · "
                             f"{pct(x.avg_trade, 3)} · {num(x.profit_factor)}")
            out.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def main(only: list[str]) -> None:
    p = Params()
    rows, rows_rg = [], []
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
            full = resample(raw, rule)
            k = int(full.index.searchsorted(pd.Timestamp(START)))
            df = full.iloc[max(0, k - WARMUP):]
            comm, slip = cost(inst, tick)
            pi = replace(p, comm=comm, slip_ticks=1)
            eq, tr = backtest(df, pi, slip)                # slip_ticks=1 × Slippage-Preis
            tr = tr[tr.entry >= pd.Timestamp(START)].reset_index(drop=True)
            tr["adx_tag"] = daily_adx_at(raw, tr.entry).round(1)
            tr["regime"] = label(tr["adx_tag"]).to_numpy()
            eq = eq[eq.index >= pd.Timestamp(START)]
            st = stats(eq, tr, df["close"][df.index >= pd.Timestamp(START)])
            base = {"instrument": inst, "name": name, "klasse": klasse, "tf": tf}
            rows.append({**base, **st})
            for rg in LABELS:
                rows_rg.append({**base, "regime": rg, **regime_stats(tr[tr.regime == rg])})
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
    r = pd.DataFrame(rows_rg)
    if only and (RES / "regime.csv").exists():
        old = pd.read_csv(RES / "regime.csv")
        r = pd.concat([old[~old.instrument.isin(only)], r])
    r.round(6).to_csv(RES / "regime.csv", index=False)
    (RES / "regime.md").write_text(regime_markdown(r))


if __name__ == "__main__":
    main(sys.argv[1:])
