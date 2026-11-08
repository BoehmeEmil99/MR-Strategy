"""Plausibilitätstests der Order-Logik auf synthetischen Daten."""
import numpy as np
import pandas as pd

from mr.engine import Params, backtest


def _ou(n=40000, seed=1):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.99 * x[i - 1] + rng.normal(0, 0.1)
    c = 100 + x
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + abs(rng.normal(0, 0.03, n))
    lo = np.minimum(o, c) - abs(rng.normal(0, 0.03, n))
    idx = pd.date_range("2020-01-01", periods=n, freq="15min")
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c}, index=idx)


def test_trades_ueberlappen_nicht_und_preise_im_balken():
    df = _ou()
    _, tr = backtest(df, Params(slip_ticks=0), 0.01)
    assert len(tr) > 100
    assert (tr.entry.iloc[1:].values >= tr.exit.iloc[:-1].values).all()
    assert (tr.exit >= tr.entry).all()
    hi, lo = df.high.reindex(tr.exit).values, df.low.reindex(tr.exit).values
    assert ((tr.exit_px.values <= hi + 1e-9) & (tr.exit_px.values >= lo - 1e-9)).all()


def test_equity_entspricht_summe_der_trades():
    df = _ou()
    p = Params()
    eq, tr = backtest(df, p, 0.01)
    # Bei 2 % Einsatz ohne Zinseszins-Effekt grob: Endkapital ≈ Start · (1 + 2 % · Σ ret)
    approx = p.capital * (1 + p.pct * tr.ret.sum())
    assert abs(eq.iloc[-1] - approx) / p.capital < 0.002


def test_zeit_stop_greift():
    df = _ou()
    _, tr = backtest(df, Params(maxBars=5), 0.01)
    assert tr.bars.max() <= 6
