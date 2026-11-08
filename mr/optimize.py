"""Parameter-Optimierung mit Out-of-Sample-Prüfung.

    python -m mr.optimize

Raster über alle Pine-Parameter, je Timeframe über alle Assets gemeinsam.
Optimiert wird nur auf TRAIN (Einstiege 2020–2023), geprüft auf TEST
(Einstiege ab 2024). Zielgröße: Durchschnitt der t-Werte der Trade-Renditen
über alle Assets. Das belohnt Vorteile, die breit und stabil sind, statt
eines einzelnen Ausreißer-Assets.

Schreibt results/optimierung_<tf>.csv (jede Kombination) und
results/optimierung.md (Zusammenfassung). Rohdaten je Asset in
results/opt_roh/<tf>.npz.
"""
from __future__ import annotations

import itertools
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from numba import njit

from .engine import Params, indicators
from .fast import trades
from .fetch import load
from .instruments import INSTRUMENTS, SPLITS
from .run import RES, TIMEFRAMES, resample

TRAIN = ("2020-01-01", "2024-01-01")
TEST = ("2024-01-01", "2100-01-01")

GRID = {
    "len":      [50, 100, 150, 200, 300, 400],      # EMA- und Sigma-Länge
    "zEntry":   [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0],
    "flat":     [0.0, 0.01, 0.02, 0.05, 0.1],       # 0 = Flat-Filter aus, sonst maxSlope
    "zTarget":  [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75],
    "stopDist": [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
    "maxBars":  [0, 25, 50, 100, 200],
}
PARAMS = list(GRID)
OUTER = list(itertools.product(GRID["len"], GRID["zEntry"], GRID["flat"]))
INNER = list(itertools.product(GRID["zTarget"], GRID["stopDist"], GRID["maxBars"]))
MIN_TRADES = 20      # Assets mit weniger Trades im Zeitraum zählen nicht
DEFAULT = {"len": 200, "zEntry": 1.5, "flat": 0.05, "zTarget": 0.0, "stopDist": 0.75, "maxBars": 100}


@njit(cache=True)
def _agg(e_idx, ret, a0, a1, b0, b1, out):
    """Summen je Zeitraum: n, Σr, Σr², Σ Gewinne, Σ Verluste."""
    for j in range(len(ret)):
        e = e_idx[j]
        p = 0 if a0 <= e < a1 else (1 if b0 <= e < b1 else -1)
        if p < 0:
            continue
        r = ret[j]
        out[p, 0] += 1; out[p, 1] += r; out[p, 2] += r * r
        if r > 0:
            out[p, 3] += r
        else:
            out[p, 4] -= r


def _one_asset(inst: str) -> tuple[str, dict]:
    tick = INSTRUMENTS[inst][2]
    raw = load(inst)
    for day, f in SPLITS.get(inst, []):
        raw.loc[raw.index < day] *= f
    base = Params()
    res = {}
    for tf, rule in TIMEFRAMES.items():
        full = resample(raw, rule)
        k = int(full.index.searchsorted(pd.Timestamp(TRAIN[0])))
        df = full.iloc[max(0, k - 3 * max(GRID["len"])):]
        ix = df.index
        a0, a1 = ix.searchsorted(pd.Timestamp(TRAIN[0])), ix.searchsorted(pd.Timestamp(TRAIN[1]))
        b0, b1 = ix.searchsorted(pd.Timestamp(TEST[0])), ix.searchsorted(pd.Timestamp(TEST[1]))
        O, H, L, C = (df[c].to_numpy() for c in ("open", "high", "low", "close"))
        slip = base.slip_ticks * tick
        out = np.zeros((len(OUTER), len(INNER), 2, 5))
        for oi, (ln, ze, fl) in enumerate(OUTER):
            p = Params(lenMu=ln, lenSig=ln, zEntry=ze, useFlat=fl > 0, maxSlope=fl or 0.05)
            ind = indicators(df["close"], p)
            mu, sg = ind.mu.to_numpy(), ind.sig.to_numpy()
            bu, se = ind.buy.to_numpy(), ind.sell.to_numpy()
            for ii, (zt, sd, mb) in enumerate(INNER):
                e, _, _, r, _ = trades(O, H, L, C, mu, sg, bu, se, zt, sd, mb, base.comm, slip)
                _agg(e, r, a0, a1, b0, b1, out[oi, ii])
        res[tf] = out.reshape(len(OUTER) * len(INNER), 2, 5)
    return inst, res


def param_frame() -> pd.DataFrame:
    rows = [(*o, *i) for o in OUTER for i in INNER]
    return pd.DataFrame(rows, columns=["len", "zEntry", "flat", "zTarget", "stopDist", "maxBars"])


def metrics(stack: np.ndarray, insts: list[str], classes: list[str] | None = None) -> pd.DataFrame:
    """stack: (Assets, Kombinationen, 2 Zeiträume, 5 Summen) -> Kennzahlen je Kombination."""
    if classes is not None:
        keep = [i for i, a in enumerate(insts) if INSTRUMENTS[a][1] in classes]
        stack = stack[keep]
    n, s, s2, w, lo = (stack[..., j] for j in range(5))
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = s / n
        var = np.clip(s2 / n - mean ** 2, 1e-18, None) * n / np.clip(n - 1, 1, None)
        t = np.where(n >= MIN_TRADES, mean / np.sqrt(var) * np.sqrt(n), np.nan)
        pos = np.where(n >= MIN_TRADES, mean > 0, np.nan)
        out = {}
        for k, name in enumerate(["train", "test"]):
            out[f"{name}_score"] = np.nanmean(t[:, :, k], axis=0)
            out[f"{name}_assets_pos"] = np.nanmean(pos[:, :, k], axis=0)
            out[f"{name}_avg_trade"] = s[:, :, k].sum(0) / n[:, :, k].sum(0)
            out[f"{name}_pf"] = w[:, :, k].sum(0) / lo[:, :, k].sum(0)
            out[f"{name}_trades"] = n[:, :, k].sum(0)
    return pd.concat([param_frame(), pd.DataFrame(out)], axis=1)


def neighbourhood(s: pd.DataFrame, row: pd.Series) -> float:
    """Ø Train-Score aller direkten Nachbarn im Raster (Robustheit)."""
    m = pd.Series(True, index=s.index)
    for c in PARAMS:
        i = GRID[c].index(row[c])
        m &= s[c].isin(GRID[c][max(0, i - 1): i + 2])
    return s.loc[m, "train_score"].mean()


def compute() -> None:
    insts = [i for i in INSTRUMENTS if load(i) is not None]
    t0 = time.time()
    results = {}
    with ProcessPoolExecutor(max_workers=2) as ex:
        for inst, res in ex.map(_one_asset, insts):
            results[inst] = res
            print(f"{INSTRUMENTS[inst][0]:28s} fertig nach {time.time() - t0:5.0f} s", flush=True)
    (RES / "opt_roh").mkdir(parents=True, exist_ok=True)
    for tf in TIMEFRAMES:
        np.savez_compressed(RES / "opt_roh" / f"{tf}.npz", insts=np.array(insts),
                            data=np.stack([results[i][tf] for i in insts]).astype(np.float32))


def load_stack(tf: str):
    z = np.load(RES / "opt_roh" / f"{tf}.npz")
    return z["data"].astype(np.float64), list(z["insts"])


if __name__ == "__main__":
    compute()
