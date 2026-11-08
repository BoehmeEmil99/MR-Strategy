"""Instrumente (Dukascopy-IDs), Asset-Klasse, Tickgröße für die Slippage.

Kupfer ist bewusst nicht enthalten.
"""
from __future__ import annotations

import json
import sys

START = "2012-01-01"   # frühester Start; spätere Instrumente beginnen mit ihrer Historie

# id: (Name, Asset-Klasse, Tickgröße, Historie ab)
INSTRUMENTS = {
    # Aktien
    "usa500idxusd":  ("S&P 500",            "Aktien",    0.01,    "2012-01-01"),
    "usatechidxusd": ("Nasdaq 100",         "Aktien",    0.01,    "2012-01-01"),
    "deuidxeur":     ("DAX",                "Aktien",    0.01,    "2013-10-01"),
    "jpnidxjpy":     ("Nikkei 225",         "Aktien",    1.0,     "2012-01-01"),
    "eemususd":      ("Emerging Markets (EEM)", "Aktien", 0.01,   "2017-02-01"),
    # Anleihen
    "tltususd":      ("US-Treasuries 20J+ (TLT)", "Anleihen", 0.01, "2017-02-01"),
    "iefususd":      ("US-Treasuries 7–10J (IEF)", "Anleihen", 0.01, "2018-02-01"),
    "bundtreur":     ("Euro-Bund",          "Anleihen",  0.01,    "2016-05-02"),
    # Credit
    "jnkususd":      ("High Yield (JNK)",   "Credit",    0.01,    "2017-02-01"),
    # Rohstoffe
    "xauusd":        ("Gold",               "Rohstoffe", 0.01,    "2012-01-01"),
    "lightcmdusd":   ("Öl WTI",             "Rohstoffe", 0.01,    "2012-01-01"),
    # Devisen
    "dollaridxusd":  ("US-Dollar-Index",    "Devisen",   0.001,   "2017-12-01"),
    "eurusd":        ("EUR/USD",            "Devisen",   0.00001, "2012-01-01"),
    "usdjpy":        ("USD/JPY",            "Devisen",   0.001,   "2012-01-01"),
    "gbpusd":        ("GBP/USD",            "Devisen",   0.00001, "2012-01-01"),
    "usdchf":        ("USD/CHF",            "Devisen",   0.00001, "2012-01-01"),
    "audusd":        ("AUD/USD",            "Devisen",   0.00001, "2012-01-01"),
    "usdcad":        ("USD/CAD",            "Devisen",   0.00001, "2012-01-01"),
    # Krypto
    "btcusd":        ("Bitcoin",            "Krypto",    0.01,    "2017-05-08"),
}

# Aktiensplits, die in den Dukascopy-Kursen nicht bereinigt sind:
# Kurse vor dem Datum werden mit dem Faktor multipliziert.
SPLITS = {
    "jnkususd": [("2019-05-06", 3.0)],   # Reverse-Split 1:3
}

if __name__ == "__main__":
    if "--json" in sys.argv:
        print(json.dumps(list(INSTRUMENTS)))
