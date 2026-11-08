"""Die schnelle Engine muss exakt dieselben Trades liefern wie die Original-Engine."""
import numpy as np
import pytest

from mr.engine import Params, backtest, indicators
from mr.fast import trades
from tests.test_engine import _ou


@pytest.mark.parametrize("kw", [{}, {"zEntry": 1.0, "stopDist": 2.0, "maxBars": 0},
                                {"useFlat": False, "zTarget": 0.5, "lenMu": 50, "lenSig": 50},
                                {"zTarget": -0.5, "stopDist": 0.5, "maxBars": 20}])
def test_gleiche_trades(kw):
    df = _ou(20000, seed=3)
    p = Params(**kw)
    _, tr = backtest(df, p, 0.01)
    ind = indicators(df["close"], p)
    e, x, s, r, w = trades(*(df[k].to_numpy() for k in ("open", "high", "low", "close")),
                           ind.mu.to_numpy(), ind.sig.to_numpy(), ind.buy.to_numpy(), ind.sell.to_numpy(),
                           p.zTarget, p.stopDist, p.maxBars, p.comm, p.slip_ticks * 0.01)
    assert len(r) == len(tr)
    np.testing.assert_allclose(r, tr.ret.to_numpy(), rtol=1e-9, atol=1e-12)
    np.testing.assert_array_equal(s, tr.side.to_numpy())
