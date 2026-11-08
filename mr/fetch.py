"""Lädt bzw. aktualisiert die 15-Minuten-Daten eines Instruments.

    python -m mr.fetch <instrument>

Speichert data/m15/<instrument>.parquet. Liegt die Datei schon vor, wird nur
ab dem letzten vorhandenen Tag nachgeladen. Geladen wird jahresweise, damit
ein Abbruch nicht alles kostet.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .instruments import INSTRUMENTS, START

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "m15"


def load(inst: str) -> pd.DataFrame | None:
    p = DATA / f"{inst}.parquet"
    return pd.read_parquet(p) if p.exists() else None


def save(inst: str, df: pd.DataFrame) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    df = df[~df.index.duplicated(keep="last")].sort_index().astype("float64")
    df.to_parquet(DATA / f"{inst}.parquet", compression="zstd")


def fetch(inst: str) -> None:
    first = max(pd.Timestamp(START), pd.Timestamp(INSTRUMENTS[inst][3])).date()
    old = load(inst)
    start = old.index[-1].date() if old is not None and len(old) else first
    end = date.today()
    df = old
    cur = start
    while cur < end:
        nxt = min(date(cur.year + 1, 1, 1), end + timedelta(days=1))
        with tempfile.NamedTemporaryFile(suffix=".csv") as tmp:
            subprocess.run(["node", str(ROOT / "fetch" / "dl.mjs"), inst,
                            cur.isoformat(), nxt.isoformat(), tmp.name], check=True)
            new = pd.read_csv(tmp.name)
        if len(new):
            new.index = pd.to_datetime(new.pop("ts"), unit="ms")
            new.index.name = "ts"
            df = new if df is None else pd.concat([df, new])
            save(inst, df)            # nach jedem Jahr sichern
        cur = nxt
    if df is None or df.empty:
        raise SystemExit(f"{inst}: keine Daten erhalten")
    print(f"{inst}: {len(df)} Kerzen, {df.index[0]} bis {df.index[-1]}")


if __name__ == "__main__":
    fetch(sys.argv[1])
