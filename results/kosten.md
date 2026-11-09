# Kostenmodell und Vergleich (Stand 9.11.2026)

Seit dieser Version rechnen alle Backtests standardmäßig mit **realistischen Kosten je Instrument** (`mr/costs.py`). Die Kosten aus dem Pine-Code (0,02 % Kommission je Seite plus 2 Ticks Slippage) gibt es weiter: mit `MR_KOSTEN=pine python -m mr.run` (gilt genauso für `mr.optimize`). Die Paper-Backtests weisen beide Varianten aus (Spalten `ret` und `ret_pine`).

## Annahmen je Seite (halber Spread + Kommission)

| Instrument | Umsetzung | Kosten je Seite |
|---|---|---|
| S&P 500, Nasdaq 100, DAX | Index-Futures (ES/MES, NQ/MNQ, FDAX/FDXM) | 0,5 bp |
| Nikkei 225 | Index-Future | 0,8 bp |
| EEM | ETF | 1,0 bp |
| TLT, IEF, JNK | ETF | 0,6 bp |
| Euro-Bund | Future | 0,5 bp |
| Gold | Future (GC/MGC) | 0,3 bp |
| Öl WTI | Future (CL/MCL) | 0,8 bp |
| EUR/USD, USD/JPY, GBP/USD | Spot bei Interactive Brokers | 0,3 bp |
| USD/CHF, AUD/USD, USD/CAD | Spot bei Interactive Brokers | 0,35 bp |
| US-Dollar-Index | Future (DX) | 0,4 bp |
| Bitcoin | Binance-Perp mit Limit-Order (Maker) | 2,0 bp (Taker: 5,0 bp) |

1 bp = 0,01 %. Zum Vergleich: Die Pine-Kosten liegen bei mindestens 2 bp je Seite, beim ES-Future mit 2 Ticks Slippage bei etwa 2,7 bp.

Grundlage: Interactive Brokers berechnet für einen ES-Kontrakt insgesamt 2,25 USD je Seite (bei rund 340.000 USD Kontraktwert unter 0,1 bp), der Spread beträgt meist 1 Tick (0,25 Punkte, etwa 0,4 bp). Spot-Devisen kosten bei IBKR 0,2 bp Kommission je Seite (mindestens 2 USD pro Order), der Ø-Spread bei EUR/USD liegt bei rund 0,23 Pips. Binance verlangt bei USDⓈ-M-Futures 0,02 % (Maker) bzw. 0,05 % (Taker). Die übrigen Werte sind aus Tickgröße, typischem Spread und Kommission geschätzt.

**Nicht enthalten:** Marktauswirkung großer Orders, Finanzierungskosten für Positionen über Nacht (bei Futures im Preis enthalten, bei CFDs nicht) und Funding-Zahlungen bei Bitcoin-Perps.

## Strategien aus den Papers: Netto je Trade in bp

Bei Pre-FOMC je Termin, bei Dash for Cash je Monat (Ø über die Assets). t-Werte für die realistischen Kosten.

| Strategie | Pine 2020–23 | Pine 2024–26 | Realistisch 2020–23 (t) | Realistisch 2024–26 (t) |
|---|---|---|---|---|
| Pre-FOMC-Drift (Lucca & Moench 2015) | +37,8 | +13,4 | +42,7 (+2,5) | +17,9 (+1,4) |
| Dash for Cash Monatsende (Etula et al. 2020) | +27,9 | +12,3 | +33,2 (+1,4) | +17,6 (+0,7) |
| Bitcoin 21–23 Uhr UTC (Padyšák & Vojtko 2022) | +3,1 | +2,4 | +3,1 (+1,2) | +2,4 (+1,2) |
| Gold Asien long / USA short (Donati & Jung 2019) | -4,0 | -1,7 | -0,4 (-0,4) | +1,9 (+1,0) |
| Noise-Area-Momentum (Zarattini et al. 2024) | -3,5 | -4,3 | +1,4 (+1,8) | +0,5 (+0,7) |
| Overnight Drift nur nach Minus-Tag | -3,8 | -2,8 | -0,7 (-1,1) | +0,2 (+0,5) |
| Opening Range Breakout 15 Min. (Zarattini & Aziz 2023) | -5,9 | -5,3 | -0,7 (-0,8) | +0,0 (+0,0) |
| Overnight Drift 2–3 Uhr ET (Boyarchenko et al. 2023) | -3,3 | -3,4 | -0,3 (-0,7) | -0,4 (-1,3) |
| FX Heimat- vs. US-Stunden (Ranaldo 2009) | -4,4 | -4,5 | -0,7 (-2,4) | -0,8 (-2,8) |
| FX-Fixing-Reversal (Krohn et al. 2024) | -3,9 | -4,6 | -0,2 (-1,3) | -0,9 (-7,1) |
| Intraday-Momentum (Gao et al. 2018) | -7,0 | -7,1 | -1,1 (-3,0) | -1,1 (-4,6) |
| Intraday-Momentum alle Klassen (Baltussen et al. 2021) | -4,3 | -5,8 | +0,2 (+0,8) | -1,4 (-10,6) |
| Intraday-Periodizität (Heston et al. 2010) | -5,4 | -5,6 | -1,2 (-6,5) | -1,4 (-8,5) |
| Bitcoin Intraday-Momentum (Shen et al. 2022) | -3,9 | -5,0 | -3,9 (-2,9) | -5,0 (-6,0) |

Bitcoin mit Market-Orders (Taker, 5 bp je Seite), Test 2024–26: 21–23-Uhr-Strategie −3,6 bp, Intraday-Momentum −11,0 bp.

**Noise-Area-Momentum nur S&P 500 und Nasdaq 100** (wofür die Strategie im Paper gebaut ist): +4,8 bp je Trade in 2020–23 (t 3,5), +1,6 bp in 2024–26 (t 1,0). Positiv in jedem Jahr, aber abnehmend: 2020 +7,4, 2021 +3,1, 2022 +4,6, 2023 +4,5, 2024 +2,3, 2025 +2,3, 2026 +0,1 bp.

## OU-Mean-Reversion (dein Pine-Code)

| | Pine-Kosten | Realistisch |
|---|---|---|
| Original-Einstellung 15m, Ø Trade ab 2020 | −5,2 bp | −1,3 bp |
| Original-Einstellung 1h | −6,6 bp | −2,6 bp |
| Original-Einstellung 4h | −6,3 bp | −2,1 bp |
| Optimale 1h-Einstellung, 2020–23 / 2024–26 | +7,2 / +5,5 bp | +11 / +9 bp |

Die neue Optimierung mit realistischen Kosten steht in `results/optimierung.md`.

## Quellen
- Interactive Brokers, Futures-Kommissionen: https://interactivebrokers.com/en/index.php?f=49560
- Interactive Brokers, Spot-Devisen: https://www.interactivebrokers.ca/en/pricing/commissions-spot-currencies.php
- ForexBrokers.com, IBKR-Spreads EUR/USD: https://www.forexbrokers.com/review/interactive-brokers/fees-features
- Binance, Futures-Gebühren: https://www.binance.com/support/faq/360033544231
