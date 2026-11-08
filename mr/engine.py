"""Python-Nachbau der Pine-Strategie "OU MR — Payoff Fixed".

Broker-Emulation wie TradingView mit process_orders_on_close=true:
- Einstieg als Market-Order zum Schlusskurs des Signalbalkens (+ Slippage).
- strategy.exit wird an jedem Balkenschluss neu gesetzt: Ziel = EMA ∓ zTarget·σE
  (wandert mit dem EMA), Stop = Einstieg ∓ stopDist·σE (σE = Sigma, eingefroren
  am ersten Balken nach dem Einstieg, wie im Pine-Code).
- Die Exit-Orders werden sofort gegen den Schlusskurs geprüft und danach
  innerhalb des nächsten Balkens. Gap über das Level -> Füllung zum Open.
  Werden Ziel und Stop im selben Balken erreicht, gilt die TradingView-Annahme:
  liegt das Hoch näher am Open, kommt zuerst das Hoch, sonst zuerst das Tief.
- Zeit-Stop: close_all zum Schlusskurs, sobald mehr als maxBars Balken offen.
- Kommission je Seite in % vom Volumen, Slippage in Ticks auf Market- und
  Stop-Orders (nicht auf Limit-Orders), Positionsgröße in % vom Eigenkapital.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Params:
    lenMu: int = 200
    lenSig: int = 200
    zEntry: float = 1.5
    zTarget: float = 0.0
    stopDist: float = 0.75
    useFlat: bool = True
    slopeLen: int = 10
    maxSlope: float = 0.05
    maxBars: int = 100
    capital: float = 100_000.0
    pct: float = 0.02          # 2 % des Eigenkapitals je Trade
    comm: float = 0.0002       # 0,02 % je Seite
    slip_ticks: int = 2


def indicators(c: pd.Series, p: Params) -> pd.DataFrame:
    mu = c.ewm(span=p.lenMu, adjust=False).mean()
    mu.iloc[: p.lenMu - 1] = np.nan
    sig = c.rolling(p.lenSig).std(ddof=0)              # ta.stdev (biased)
    sig = sig.where(sig != 0)
    z = (c - mu) / sig
    slope = (mu - mu.shift(p.slopeLen)).abs() / p.slopeLen / sig
    flat = (slope <= p.maxSlope) if p.useFlat else pd.Series(True, index=c.index)
    zp = z.shift(1)
    buy = (z > -p.zEntry) & (zp <= -p.zEntry) & flat & z.notna()    # crossover
    sell = (z < p.zEntry) & (zp >= p.zEntry) & flat & z.notna()     # crossunder
    return pd.DataFrame({"mu": mu, "sig": sig, "z": z, "buy": buy, "sell": sell})


def backtest(df: pd.DataFrame, p: Params, tick: float):
    """df: Spalten open, high, low, close. Gibt (Equity, Trades) zurück."""
    ind = indicators(df["close"], p)
    mu, sg = ind["mu"].to_numpy(), ind["sig"].to_numpy()
    buy, sell = ind["buy"].to_numpy(), ind["sell"].to_numpy()
    O, H, L, C = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    idx = df.index
    slip = p.slip_ticks * tick
    n = len(C)

    cash = p.capital
    pos = 0.0
    avg = np.nan
    e_i = -1
    sigE = np.nan
    lim = stp = np.nan
    trades = []
    eq = np.empty(n)

    def close_pos(px, i, why):
        nonlocal cash, pos, avg, e_i, sigE, lim, stp
        side = 1.0 if pos > 0 else -1.0
        q = abs(pos)
        cash += side * q * (px - avg) - p.comm * q * px
        trades.append((idx[e_i], idx[i], int(side), avg, px, i - e_i,
                       side * (px / avg - 1) - p.comm * (1 + px / avg), why))
        pos, avg, e_i, sigE, lim, stp = 0.0, np.nan, -1, np.nan, np.nan, np.nan

    for i in range(n):
        # 1) Exit-Orders vom letzten Balkenschluss intraday prüfen
        if pos != 0 and not np.isnan(lim):
            o, h, l = O[i], H[i], L[i]
            high_first = (h - o) <= (o - l)
            if pos > 0:
                if o >= lim:
                    close_pos(o, i, "ziel")
                elif o <= stp:
                    close_pos(o - slip, i, "stop")
                else:
                    t, s = h >= lim, l <= stp
                    if t and (high_first or not s):
                        close_pos(lim, i, "ziel")
                    elif s:
                        close_pos(stp - slip, i, "stop")
            else:
                if o <= lim:
                    close_pos(o, i, "ziel")
                elif o >= stp:
                    close_pos(o + slip, i, "stop")
                else:
                    t, s = l <= lim, h >= stp
                    if s and (high_first or not t):
                        close_pos(stp + slip, i, "stop")
                    elif t:
                        close_pos(lim, i, "ziel")

        # 2) Skript läuft am Balkenschluss (Position vor neuen Fills)
        flat_now = pos == 0
        go_long = flat_now and buy[i]
        go_short = flat_now and sell[i] and not go_long
        if not flat_now:
            if np.isnan(sigE):
                sigE = sg[i]
            if pos > 0:
                lim, stp = mu[i] - p.zTarget * sigE, avg - p.stopDist * sigE
                if C[i] >= lim:
                    close_pos(C[i], i, "ziel")
                elif C[i] <= stp:
                    close_pos(C[i] - slip, i, "stop")
            else:
                lim, stp = mu[i] + p.zTarget * sigE, avg + p.stopDist * sigE
                if C[i] <= lim:
                    close_pos(C[i], i, "ziel")
                elif C[i] >= stp:
                    close_pos(C[i] + slip, i, "stop")
            if pos != 0 and p.maxBars > 0 and i - e_i > p.maxBars:
                close_pos(C[i] - np.sign(pos) * slip, i, "zeit")

        # 3) Einstieg zum Schlusskurs
        if go_long or go_short:
            px = C[i] + slip if go_long else C[i] - slip
            q = p.pct * cash / C[i]
            cash -= p.comm * q * px
            pos, avg, e_i = (q if go_long else -q), px, i

        eq[i] = cash + (pos * (C[i] - avg) if pos != 0 else 0.0)

    if pos != 0:
        close_pos(C[-1], n - 1, "offen")
        eq[-1] = cash
    tr = pd.DataFrame(trades, columns=["entry", "exit", "side", "entry_px",
                                       "exit_px", "bars", "ret", "why"])
    return pd.Series(eq, index=idx), tr


def stats(eq: pd.Series, tr: pd.DataFrame, close: pd.Series) -> dict:
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    out = {"von": eq.index[0].date().isoformat(), "bis": eq.index[-1].date().isoformat(),
           "jahre": round(yrs, 1), "trades": len(tr)}
    if len(tr):
        w, lo = tr.ret[tr.ret > 0], tr.ret[tr.ret <= 0]
        out.update({
            "trades_pro_jahr": len(tr) / yrs,
            "trefferquote": (tr.ret > 0).mean(),
            "avg_trade": tr.ret.mean(),
            "avg_gewinn": w.mean() if len(w) else np.nan,
            "avg_verlust": lo.mean() if len(lo) else np.nan,
            "payoff": (w.mean() / -lo.mean()) if len(w) and len(lo) else np.nan,
            "profit_factor": (w.sum() / -lo.sum()) if lo.sum() < 0 else np.inf,
            "long": int((tr.side > 0).sum()),
            "short": int((tr.side < 0).sum()),
            "avg_long": tr.ret[tr.side > 0].mean(),
            "avg_short": tr.ret[tr.side < 0].mean(),
            "avg_bars": tr.bars.mean(),
            "exit_ziel": int((tr.why == "ziel").sum()),
            "exit_stop": int((tr.why == "stop").sum()),
            "exit_zeit": int((tr.why == "zeit").sum()),
            "summe_trades": tr.ret.sum(),
        })
    total = eq.iloc[-1] / eq.iloc[0]
    out.update({
        "rendite": total - 1,
        "cagr": total ** (1 / yrs) - 1 if yrs > 0 else np.nan,
        "max_dd": (eq / eq.cummax() - 1).min(),
        "bh_cagr": (close.iloc[-1] / close.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan,
    })
    return out
