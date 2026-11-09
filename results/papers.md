# Strategien aus Forschungsarbeiten (Stand 9.11.2026)

Code: `mr/papers.py`, alle Trades: `results/papers/trades.parquet` (nicht im Repo, mit `python -m mr.papers` erzeugen).

**Vorgehen wie beim OU-Backtest:** gleiche Dukascopy-Daten (15 Minuten), gleiche Kosten (0,02 % Kommission je Seite + 2 Ticks Slippage), Train = Einstiege 2020–2023, Test = Einstiege ab 2024. Alle Strategien sind über Uhrzeiten definiert. Deshalb gibt es hier keine Aufteilung in 15m, 1h und 4h: Gehandelt wird zu den Zeiten, die das Paper vorgibt, ausgeführt zum Schlusskurs des 15-Minuten-Balkens. Fast alle Paper-Stichproben enden vor 2020, für sie ist also auch der Train-Zeitraum schon Neuland.

**Brutto** = vor Kosten, **netto** = nach Kosten, Angaben in Basispunkten (bp, 1 bp = 0,01 %) je Trade. **Break-even** = Kosten je Seite, bei denen der Brutto-Vorteil genau aufgezehrt ist. Die Pine-Kosten liegen bei mindestens 2 bp je Seite.

## Übersicht

| Strategie | Trades/Jahr | Brutto Train (t) | Brutto Test (t) | Netto Train | Netto Test | Break-even je Seite (Test) |
|---|---|---|---|---|---|---|
| Pre-FOMC-Drift, je Termin | 8 | **+44 bp (2,6)** | **+19 bp (1,5)** | +38 bp | +13 bp | 9,6 bp |
| Bitcoin 21–23 Uhr UTC | 360 | **+7,1 bp (2,8)** | **+6,4 bp (3,1)** | +3,1 bp | +2,4 bp | 3,2 bp |
| Overnight Drift 2–3 Uhr ET | 620 | +0,7 bp (1,8) | +0,6 bp (2,0) | −3,3 bp | −3,4 bp | 0,3 bp |
| Overnight Drift nur nach Minus-Tag | 230 | +0,3 bp (0,5) | +1,2 bp (2,4) | −3,8 bp | −2,8 bp | 0,6 bp |
| Intraday-Momentum alle Klassen | 5.600 | +1,3 bp (6,2) | −0,2 bp (−1,6) | −4,3 bp | −5,8 bp | – |
| FX-Fixing-Reversal | 8.100 | +0,5 bp (4,2) | −0,2 bp (−1,5) | −3,9 bp | −4,6 bp | – |
| Intraday-Momentum (erste/letzte halbe Stunde) | 1.600 | +0,2 bp (0,5) | +0,2 bp (0,7) | −7,0 bp | −7,1 bp | 0,1 bp |
| Intraday-Periodizität | 10.100 | 0,0 bp (−0,1) | −0,3 bp (−1,5) | −5,4 bp | −5,6 bp | – |

Achtung beim t-Wert: Bei Strategien, die mehrere Assets zur selben Zeit handeln, überschätzt der gepoolte t-Wert die Sicherheit, weil die Assets korreliert sind. Für FOMC ist er deshalb je Termin berechnet (Ø über die 5 Indizes).

## Die Strategien im Einzelnen

**1. Pre-FOMC-Drift.** Lucca & Moench (2015, Journal of Finance): Aktien steigen in den 24 Stunden vor dem Zinsentscheid der Fed. Umsetzung: S&P 500, Nasdaq 100, DAX, Nikkei 225 und EEM long von 13:45 ET am Vortag bis 13:45 ET am Entscheidungstag, 54 geplante Termine (ohne die Notfallsitzungen im März 2020). Ergebnis: +0,44 % je Termin in 2020–23 und +0,19 % in 2024–26. An allen anderen Tagen bringt dasselbe 24-Stunden-Fenster im Schnitt nur +0,04 %. Positiv in 6 von 7 Jahren, Trefferquote rund 60 %. Mit nur 8 Terminen pro Jahr bleibt die Unsicherheit groß, und im Testzeitraum ist der t-Wert nicht signifikant.

**2. Bitcoin 21–23 Uhr UTC.** Padyšák & Vojtko (2022, SSRN): BTC steigt überdurchschnittlich zwischen 21 und 23 Uhr UTC, also rund um den US-Börsenschluss. Ergebnis: in beiden Zeiträumen etwa +7 bp brutto je Tag, die Einzelstunden 21 und 22 Uhr sind jeweils für sich positiv. Nach den Pine-Kosten bleiben +2 bis +3 bp, das ist nicht signifikant (t etwa 1,2). Break-even liegt bei gut 3 bp je Seite: Mit Maker-Gebühren ginge das, mit Taker-Gebühren (meist 4–10 bp) nicht. 2022 war negativ (−4,5 bp), 2026 bisher bei null.

**3. Overnight Drift.** Boyarchenko, Larsen & Whelan (2023, Review of Financial Studies): Fast die gesamte Aktienrendite von 1998–2019 entstand zwischen 2 und 3 Uhr ET, beim Börsenstart in Europa. Umsetzung: S&P 500 und Nasdaq 100 jeden Tag long 02:00–03:00 ET, als Variante nur nach einem Minus-Tag in den USA (die Autoren finden den Effekt vor allem nach Ausverkäufen). Ergebnis: Brutto nur noch +0,6 bis +1,2 bp, das ist weit unter den Kosten. Die Autoren schreiben selbst, dass der Effekt seit 2021 verschwunden ist.

**4. Intraday-Momentum über alle Asset-Klassen.** Baltussen, Da, Lammers & Martens (2021, Journal of Financial Economics): Die Rendite vom Vortagesschluss bis 30 Minuten vor Handelsschluss sagt die Richtung der letzten 30 Minuten voraus, erklärt durch Gamma-Hedging. Umsetzung: alle 19 Assets mit ihrer jeweiligen Schlusszeit (z. B. 16:00 ET für US-Aktien, 17:30 Uhr für den DAX, 13:30 ET für Gold, 15:00 ET für Devisen). Ergebnis: in 2020–23 klar vorhanden (+1,3 bp brutto, t 6,2), seit 2024 verschwunden. Selbst in 2020–23 liegt der Vorteil weit unter den Kosten.

**5. FX-Fixing-Reversal.** Krohn, Mueller & Whelan (2024, Journal of Finance): Der Dollar steigt vor den großen Devisen-Fixings (Tokio 9:55 Uhr Ortszeit, EZB, London 16 Uhr) und fällt danach. Umsetzung: vier Fenster pro Tag wie im Paper (USD long 17:00 ET → Tokio-Fix, USD short bis 02:00 ET, USD long 02:00–08:15 ET, USD short 11:00–17:00 ET) für 6 Währungspaare und den Dollar-Index. Ergebnis: in 2020–23 noch messbar (+0,5 bp, t 4,2), seit 2024 weg. Die Autoren kommen schon mit vollem Spread auf negative Renditen.

**6. Intraday-Momentum erste/letzte halbe Stunde.** Gao, Han, Li & Zhou (2018, Journal of Financial Economics): Die Rendite vom Vortagesschluss bis 10:00 ET sagt die Richtung von 15:30–16:00 ET voraus. Umsetzung: S&P 500, Nasdaq 100, EEM, TLT, IEF, JNK. Ergebnis: kein Effekt mehr (+0,2 bp, Studienzeitraum endete 2013).

**7. Intraday-Periodizität.** Heston, Korajczyk & Sadka (2010, Journal of Finance): Renditen wiederholen sich zur selben Uhrzeit an den Folgetagen. Im Paper geht es um Einzelaktien im Querschnitt, hier umgesetzt als Zeitreihen-Variante für alle 19 Assets: jeden Tag long in der Stunde mit der besten und short in der mit der schlechtesten Ø-Rendite der letzten 40 Tage. Ergebnis: kein Effekt.

## Trend vs. Konsolidierung (Tages-ADX vom Vortag, netto bp je Trade)

| Strategie | Konsolidierung | Übergang | Trend |
|---|---|---|---|
| Pre-FOMC (je Trade) | +23,5 | +47,7 | +23,1 |
| Bitcoin 21–23 Uhr | +1,9 | −2,8 | +5,3 |
| Overnight Drift | −3,8 | −3,4 | −3,0 |
| Intraday-Momentum alle Klassen | −5,6 | −5,1 | −4,1 |
| FX-Fixing-Reversal | −4,4 | −4,2 | −4,0 |
| Intraday-Momentum erste/letzte halbe Stunde | −7,6 | −7,6 | −5,8 |
| Intraday-Periodizität | −5,7 | −5,2 | −5,5 |

Nur bei BTC hilft der Filter erkennbar: Die Abendstunden laufen in Trendphasen besser. Die Momentum-Strategien schneiden im Trend etwas weniger schlecht ab, das reicht aber bei Weitem nicht für ein positives Ergebnis.

## Einschränkungen
- Daten sind Dukascopy-CFDs (Bid). ETF-CFDs (EEM, TLT, IEF, JNK) handeln nur zu US-Börsenzeiten.
- Ein- und Ausstieg zum 15-Minuten-Raster: Den Tokio-Fix um 9:55 Uhr handle ich um 10:00 Uhr.
- Für Devisen gibt es keinen Börsenschluss. Bei Baltussen et al. nehme ich 15:00 ET (Schluss der CME-Devisenfutures), bei BTC 00:00 UTC.

## Quellen
- Lucca, Moench (2015): The Pre-FOMC Announcement Drift, Journal of Finance 70(1). https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf
- Kurov, Wolfe, Gilbert (2021): The Disappearing Pre-FOMC Announcement Drift. https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf
- Padyšák, Vojtko (2022): Seasonality, Trend-following, and Mean reversion in Bitcoin, SSRN. Zusammenfassung: https://quantpedia.com/the-seasonality-of-bitcoin/
- Boyarchenko, Larsen, Whelan (2023): The Overnight Drift, Review of Financial Studies 36(9). https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf
- Boyarchenko, Larsen, Whelan (2026): The Disappearing Overnight Drift. https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/
- Baltussen, Da, Lammers, Martens (2021): Hedging Demand and Market Intraday Momentum, Journal of Financial Economics 142(1). https://www3.nd.edu/~zda/intramom.pdf
- Krohn, Mueller, Whelan (2024): Foreign Exchange Fixings and Returns around the Clock, Journal of Finance 79(1). https://www.bankofcanada.ca/wp-content/uploads/2021/10/swp2021-48.pdf
- Gao, Han, Li, Zhou (2018): Market Intraday Momentum, Journal of Financial Economics 129(2). https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414
- Heston, Korajczyk, Sadka (2010): Intraday Patterns in the Cross-section of Stock Returns, Journal of Finance 65(4). https://arxiv.org/pdf/1005.3535.pdf
