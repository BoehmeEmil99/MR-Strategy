"""Schnelle (numba) Variante von engine.backtest für die Parameter-Optimierung.

Gleiche Order-Logik wie mr/engine.py, liefert aber nur die Trades
(Renditen je Trade sind unabhängig von der Positionsgröße).
Abgleich mit der Original-Engine in tests/test_fast.py.
"""
from __future__ import annotations

import numpy as np
from numba import njit

ZIEL, STOP, ZEIT, OFFEN = 0, 1, 2, 3


@njit(cache=True)
def trades(O, H, L, C, mu, sg, buy, sell, zTarget, stopDist, maxBars, comm, slip):
    n = len(C)
    e_idx = np.empty(n // 2 + 1, np.int64)
    x_idx = np.empty(n // 2 + 1, np.int64)
    side_a = np.empty(n // 2 + 1, np.int8)
    ret_a = np.empty(n // 2 + 1, np.float64)
    why_a = np.empty(n // 2 + 1, np.int8)
    k = 0
    pos = 0          # +1 / -1 / 0
    avg = np.nan
    e_i = -1
    sigE = np.nan
    lim = np.nan
    stp = np.nan

    for i in range(n):
        px = np.nan
        why = -1
        # 1) Intraday-Prüfung der Levels vom Vortag
        if pos != 0 and not np.isnan(lim):
            o = O[i]; h = H[i]; l = L[i]
            high_first = (h - o) <= (o - l)
            if pos > 0:
                if o >= lim:
                    px = o; why = ZIEL
                elif o <= stp:
                    px = o - slip; why = STOP
                else:
                    t = h >= lim; s = l <= stp
                    if t and (high_first or not s):
                        px = lim; why = ZIEL
                    elif s:
                        px = stp - slip; why = STOP
            else:
                if o <= lim:
                    px = o; why = ZIEL
                elif o >= stp:
                    px = o + slip; why = STOP
                else:
                    t = l <= lim; s = h >= stp
                    if s and (high_first or not t):
                        px = stp + slip; why = STOP
                    elif t:
                        px = lim; why = ZIEL
            if why >= 0:
                e_idx[k] = e_i; x_idx[k] = i; side_a[k] = pos; why_a[k] = why
                ret_a[k] = pos * (px / avg - 1) - comm * (1 + px / avg); k += 1
                pos = 0; avg = np.nan; e_i = -1; sigE = np.nan; lim = np.nan; stp = np.nan

        # 2) Balkenschluss
        flat_now = pos == 0
        go_long = flat_now and buy[i]
        go_short = flat_now and sell[i] and not go_long
        if not flat_now:
            if np.isnan(sigE):
                sigE = sg[i]
            why = -1
            if pos > 0:
                lim = mu[i] - zTarget * sigE; stp = avg - stopDist * sigE
                if C[i] >= lim:
                    px = C[i]; why = ZIEL
                elif C[i] <= stp:
                    px = C[i] - slip; why = STOP
            else:
                lim = mu[i] + zTarget * sigE; stp = avg + stopDist * sigE
                if C[i] <= lim:
                    px = C[i]; why = ZIEL
                elif C[i] >= stp:
                    px = C[i] + slip; why = STOP
            if why < 0 and maxBars > 0 and i - e_i > maxBars:
                px = C[i] - pos * slip; why = ZEIT
            if why >= 0:
                e_idx[k] = e_i; x_idx[k] = i; side_a[k] = pos; why_a[k] = why
                ret_a[k] = pos * (px / avg - 1) - comm * (1 + px / avg); k += 1
                pos = 0; avg = np.nan; e_i = -1; sigE = np.nan; lim = np.nan; stp = np.nan

        # 3) Einstieg
        if go_long:
            pos = 1; avg = C[i] + slip; e_i = i
        elif go_short:
            pos = -1; avg = C[i] - slip; e_i = i

    if pos != 0:
        px = C[n - 1]
        e_idx[k] = e_i; x_idx[k] = n - 1; side_a[k] = pos; why_a[k] = OFFEN
        ret_a[k] = pos * (px / avg - 1) - comm * (1 + px / avg); k += 1
    return e_idx[:k], x_idx[:k], side_a[:k], ret_a[:k], why_a[:k]
