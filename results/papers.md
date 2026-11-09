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

---

# Runde 2 (Stand 9.11.2026)

Code: `mr/papers2.py` (`python -m mr.papers2`), gleiche Daten, Kosten und Train/Test-Aufteilung.

## Übersicht

| Strategie | Trades/Jahr | Brutto Train (t) | Brutto Test (t) | Netto Train | Netto Test | Break-even je Seite (Test) |
|---|---|---|---|---|---|---|
| Dash for Cash (Monatsende), je Monat | 12 | +34 bp (1,4) | +19 bp (0,7) | +28 bp | +12 bp | 9,4 bp |
| Noise-Area-Momentum | 1.200 | **+2,6 bp (3,4)** | **+1,7 bp (2,1)** | −3,5 bp | −4,3 bp | 0,9 bp |
| Gold Asien long / USA short | 570 | +0,2 bp (0,2) | +2,5 bp (1,4) | −4,0 bp | −1,7 bp | 1,2 bp |
| Opening Range Breakout (15 Min.) | 1.200 | +0,6 bp (0,6) | +1,3 bp (1,5) | −5,9 bp | −5,3 bp | 0,6 bp |
| Bitcoin Intraday-Momentum | 350 | +0,1 bp (0,1) | −1,0 bp (−1,2) | −3,9 bp | −5,0 bp | – |
| FX Heimat- vs. US-Stunden | 3.000 | 0,0 bp (−0,1) | −0,1 bp (−0,5) | −4,4 bp | −4,5 bp | – |

## Die Strategien im Einzelnen

**1. Dash for Cash.** Etula, Rinne, Suominen & Vaittinen (2020, Review of Financial Studies): Pensionsfonds und andere Institutionen verkaufen vor dem Monatsende Aktien, um Auszahlungen zu decken. Bis zum letzten Verkaufstag (bedingt durch die Abwicklungsfrist) fallen die Kurse, danach erholen sie sich. Umsetzung: Aktien (S&P 500, Nasdaq 100, EEM, DAX, Nikkei) long vom letzten Verkaufstag bis 3 Handelstage nach Monatsende. Der letzte Verkaufstag ist bei US-Aktien T−3 bis Mai 2024 und T−2 seit der Umstellung auf T+1-Abwicklung, bei DAX und Nikkei T−3. Treasuries (TLT, IEF) long ab T−2. Ergebnis: +0,34 % je Monat in 2020–23, +0,19 % in 2024–26. Ein Teil davon ist aber nur der allgemeine Aufwärtstrend. Gegen beliebige gleich lange Haltefenster lagen US-Aktien in 2020–23 um 0,4–0,6 Prozentpunkte vorn, in 2024–26 nicht mehr (S&P 500: 0,35 % gegenüber 0,42 % in beliebigen Fenstern). Kein belastbarer Effekt mehr.

**2. Noise-Area-Momentum.** Zarattini, Aziz & Barbon (2024, Swiss Finance Institute): Aus der Ø-Bewegung seit Eröffnung der letzten 14 Tage wird je Uhrzeit ein „Rausch-Band“ berechnet. Bricht der Kurs zur vollen oder halben Stunde aus dem Band aus, wird in Ausbruchsrichtung gehandelt. Ausstieg, wenn der Kurs zurück ins Band fällt, spätestens zum Handelsschluss. Umsetzung: S&P 500, Nasdaq 100, DAX, EEM, TLT, ohne den VWAP-Stop des Papers (keine Volumendaten). Ergebnis: Der Brutto-Vorteil ist in jedem Jahr positiv (+0,8 bis +3,5 bp) und auch im Test signifikant (t 2,1), am stärksten bei S&P 500 und Nasdaq 100. Er liegt aber unter den Pine-Kosten: Break-even sind rund 1 bp je Seite. Mit Index-Futures (z. B. ES, Kosten typischerweise unter 1 bp je Seite) läge die Strategie etwa bei null. Von den getesteten Strategien ist sie die stabilste, aber nur mit sehr günstiger Ausführung interessant.

**3. Gold Asien long / USA short.** In einer Masterarbeit an der CBS (Donati & Jung 2019, betreut von Paul Whelan) steigt Gold robust in asiatischen Handelsstunden und fällt im Rest des Tages. Als Masterarbeit ist das die schwächste Quelle dieser Runde. Umsetzung: Gold long 00:00–07:00 UTC, short 13:00–20:00 UTC. Ergebnis: in 2020–23 nichts, 2024–26 +2,5 bp brutto (t 1,4), vor allem über das Asien-Bein.

**4. Opening Range Breakout.** Zarattini & Aziz (2023, SSRN): Richtung der ersten 5 Minuten handeln, Stop am Tief bzw. Hoch dieser Kerze, Ziel 10-faches Risiko, sonst Ausstieg zum Schluss. Umsetzung mit der ersten 15-Minuten-Kerze (kürzere Daten haben wir nicht) auf S&P 500, Nasdaq 100, DAX, EEM, TLT. Ergebnis: +0,6 bis +1,3 bp brutto, netto klar negativ. Das passt zu einer unabhängigen Nachrechnung auf fünf Index-CFDs, die vor Kosten das Paper bestätigt, nach Kosten aber bei null landet.

**5. Bitcoin Intraday-Momentum.** Shen, Urquhart & Wang (2022, Financial Review): Die erste halbe Stunde des Tages sagt die letzte halbe Stunde voraus. Umsetzung mit dem UTC-Tag. Ergebnis: kein Effekt.

**6. FX Heimat- vs. US-Stunden.** Ranaldo (2009, Journal of Banking & Finance): Währungen werten während der eigenen Arbeitszeit ab und während der Arbeitszeit des Auslands auf. Umsetzung für EUR, GBP, CHF, JPY und AUD gegen USD: USD long in den Heimat-Stunden, USD short in den US-Stunden. Ergebnis: kein Effekt mehr (Studienzeitraum endete 2005).

## Trend vs. Konsolidierung (netto bp je Trade)

| Strategie | Konsolidierung | Übergang | Trend |
|---|---|---|---|
| Dash for Cash | +9,9 | +68,5 | +12,9 |
| Noise-Area-Momentum | −4,0 | −5,9 | −2,1 |
| Gold Asien/USA | −4,7 | +0,2 | −3,1 |
| Opening Range Breakout | −5,2 | −5,9 | −6,1 |
| Bitcoin Intraday-Momentum | −3,2 | −1,9 | −5,9 |
| FX Heimat/US | −4,6 | −4,1 | −4,5 |

Noise-Area-Momentum läuft wie erwartet in Trendphasen am besten (brutto +3,4 bp gegenüber +2,4 bp in Konsolidierung). Ein Trendfilter allein reicht aber nicht, um die Kosten zu decken.

## Quellen Runde 2
- Etula, Rinne, Suominen, Vaittinen (2020): Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs, Review of Financial Studies 33(1). https://acris.aalto.fi/ws/portalfiles/portal/40965155/hhz054.pdf
- Zarattini, Aziz, Barbon (2024): Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY), SFI Research Paper 24-97. https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy
- Zarattini, Aziz (2023): Can Day Trading Really Be Profitable?, SSRN 4416622. https://papers.ssrn.com/abstract=4416622
- Nachrechnung des ORB auf Index-CFDs: https://www.mql5.com/en/blogs/post/776235
- Shen, Urquhart, Wang (2022): Bitcoin Intraday Time-Series Momentum, Financial Review 57(2). https://research.birmingham.ac.uk/en/publications/bitcoin-intraday-time-series-momentum/
- Ranaldo (2009): Segmentation and Time-of-Day Patterns in Foreign Exchange Markets, Journal of Banking & Finance 33(12). https://econpapers.repec.org/RePEc:eee:jbfina:v:33:y:2009:i:12:p:2199-2206
- Donati, Jung (2019): Gold Price Dynamics Around the Clock, Masterarbeit CBS. https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/
