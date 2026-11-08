# mr-strategy

Backtest der Pine-Strategie **„OU MR — Payoff Fixed“** (Ornstein-Uhlenbeck Mean Reversion) auf 15m, 1h und 4h über die wichtigsten Asset-Klassen.

## Ablauf
1. Im Tab **Actions** „Daten laden und Backtest“ öffnen und **Run workflow** tippen.
2. Der Workflow lädt für jedes Instrument die 15-Minuten-Kerzen von Dukascopy (parallel, beim ersten Lauf dauert das eine Weile). Daraus werden 1h- und 4h-Kerzen gebildet.
3. Danach läuft der Backtest **ab 2020** (`START` in `mr/run.py`). Die Ergebnisse landen in `results/summary.md` (Übersicht), `results/regime.md` (Trend vs. Konsolidierung), den passenden CSV-Dateien und `results/trades/` (jeder einzelne Trade mit Regime beim Einstieg).

Spätere Läufe laden nur die neuen Tage nach. Mit `nur_backtest = true` läuft nur der Backtest auf den vorhandenen Daten, zum Beispiel nach einer Parameter-Änderung.

## Strategie
Parameter wie im Pine-Code (`mr/engine.py`, Klasse `Params`):

| Parameter | Wert |
|---|---|
| EMA-/Sigma-Länge | 200 / 200 |
| Entry-Z | 1,5 (Einstieg, wenn Z von außen zurück durch ±1,5 kreuzt) |
| Ziel | EMA (0 σ) |
| Stop | 0,75 σ ab Einstieg, Sigma beim Einstieg eingefroren |
| Flat-Filter | an, max. Slope 0,05 σ je Balken über 10 Balken |
| Zeit-Stop | 100 Balken |
| Positionsgröße | **2 %** des Eigenkapitals |
| Kosten | 0,02 % Kommission je Seite, 2 Ticks Slippage |

Die Order-Ausführung bildet TradingView mit `process_orders_on_close=true` nach: Einstieg zum Schlusskurs, Ziel und Stop werden an jedem Balkenschluss neu gesetzt und im nächsten Balken intraday geprüft. Gaps werden zum Open gefüllt. Wenn Ziel und Stop im selben Balken liegen, gilt dieselbe Annahme wie bei TradingView: Liegt das Hoch näher am Open, kommt das Hoch zuerst.

## Trend vs. Konsolidierung
Jeder Trade bekommt das Marktregime beim Einstieg: Tages-ADX(14) des Vortags ab 25 = Trend, unter 20 = Konsolidierung, dazwischen Übergang (`mr/regime.py`). Bewusst nicht der ADX auf dem Trade-Timeframe, denn der misst beim Einstieg genau die Bewegung, gegen die die Strategie handelt.

## Instrumente
Siehe `mr/instruments.py`. Daten ab 2012 bzw. ab Verfügbarkeit bei Dukascopy, gezählt werden Trades ab 2020.

- **Aktien:** S&P 500, Nasdaq 100, DAX, Nikkei 225, Emerging Markets (EEM)
- **Anleihen:** US-Treasuries 20J+ (TLT), 7–10J (IEF), Euro-Bund
- **Credit:** High Yield (JNK)
- **Rohstoffe:** Gold, Öl WTI
- **Devisen:** US-Dollar-Index, EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD
- **Krypto:** Bitcoin

## Einschränkungen
- **Spread:** Die Kurse sind Bid-Kurse. Den Spread zahlt man in der Realität zusätzlich zu Kommission und Slippage, was besonders auf 15m ins Gewicht fällt.
- **CFD-Kurse:** Indizes und Rohstoffe sind Dukascopy-CFDs, keine Futures. Die Handelszeiten weichen leicht ab.
- **4h-Kerzen:** Sie beginnen um 0, 4, 8 … Uhr UTC. TradingView beginnt bei Devisen am Sessionstart, dadurch können einzelne Signale abweichen.

## Lokal
```bash
npm ci && pip install -r requirements.txt
python -m mr.fetch eurusd      # Daten eines Instruments laden
python -m mr.run               # Backtest
python -m pytest tests         # Tests der Order-Logik
python -m mr.optimize          # Parameter-Raster (Ergebnis: results/optimierung.md)
```
