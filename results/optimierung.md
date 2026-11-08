# Parameter-Optimierung (Stand 8.11.2026)

**Vorgehen:** Raster über alle Pine-Parameter (50.400 Kombinationen je Timeframe, Code in `mr/optimize.py`), getestet auf allen 19 Assets gleichzeitig. Optimiert wurde nur auf **2020–2023** (Train). **2024–2026** (Test) hat die Optimierung nie gesehen und dient als Prüfung. Zielgröße ist der Ø t-Wert der Trade-Renditen über alle Assets. So gewinnt eine Einstellung, die breit funktioniert, und nicht eine, die zufällig bei einem Asset gut aussieht. Kosten wie im Pine-Code: 0,02 % Kommission je Seite, 2 Ticks Slippage.

Getestete Werte:

| Parameter | Werte |
|---|---|
| EMA-/Sigma-Länge | 50, 100, 150, 200, 300, 400 (Nachtest bis 800) |
| Entry-Z | 1,0 – 3,0 (Nachtest bis 4,0) |
| Flat-Filter (max. Slope) | aus, 0,01, 0,02, 0,05, 0,1 |
| Ziel vor dem Mittelwert | −0,5 bis +0,75 σ (Nachtest bis −1,0) |
| Stop ab Einstieg | 0,25 – 5 σ (Nachtest bis 10 σ) |
| Zeit-Stop | aus, 25, 50, 100, 200 Balken (Nachtest bis 400) |

## Ergebnis: beste Einstellung je Timeframe

| | 15m | 1h | 4h |
|---|---|---|---|
| EMA-/Sigma-Länge | 200 | **300** | 200 |
| Entry-Z | 2,5 | **3,0** | 2,5 |
| Flat-Filter | 0,01 | **0,02** | aus |
| Ziel | 0,5 σ hinter dem EMA | **0,25 σ hinter dem EMA** | 0,75 σ vor dem EMA |
| Stop | 5 σ | **5 σ** | 5 σ |
| Zeit-Stop | aus | **aus** | aus |
| Ø Trade 2020–23 | −0,008 % | **+0,072 %** | −0,145 % |
| Ø Trade 2024–26 (Test) | −0,033 % | **+0,055 %** | +0,024 % |
| Profit Factor 2020–23 / Test | 0,97 / 0,88 | **1,08 / 1,06** | 0,89 / 1,03 |
| t-Wert 2020–23 / Test | −0,2 / −0,9 | **0,55 / 0,38** | −0,6 / 0,1 |
| Trades 2020–26 (alle Assets) | 1.060 | **1.084** | 860 |
| Trefferquote | 69 % | **66 %** | 70 % |

Zum Vergleich deine Original-Einstellung auf 1h ab 2020: 13.614 Trades, Ø −0,066 %, Profit Factor 0,87.

Für Pine („Ziel vor dem Mittelwert“): ein Ziel hinter dem EMA ist ein negativer Wert, z. B. −0,25.

## Was die Optimierung zeigt
- **Klare Richtung, stabil in beiden Zeiträumen:** längere EMA/Sigma, höheres Entry-Z, Stop weit weg (praktisch nur Notfall-Stop), kein Zeit-Stop, Ziel eher hinter dem EMA. Die Rangfolge der Kombinationen in Train und Test stimmt stark überein (Rangkorrelation 0,99 / 0,92 / 0,70 für 15m / 1h / 4h).
- **Aber kein belastbarer Vorteil:** Auf 15m ist keine einzige Kombination in 2020–23 im Plus. Auf 1h und 4h sind es 0,2 % bzw. 0,3 % aller Kombinationen. Die beste 1h-Einstellung ist in beiden Zeiträumen leicht positiv, ihr t-Wert liegt mit 0,4–0,6 aber weit unter dem, was man für einen echten Vorteil bräuchte (ab etwa 2).
- **Der enge Stop war das Hauptproblem:** Mit 0,75 σ endeten 56 % der Trades am Stop, mit 5 σ sind es 18 %. Die Trefferquote steigt dadurch von 40 % auf 66 %.
- **Nach Jahren schwankt die 1h-Einstellung stark:** 2020 −0,34 %, 2021 +0,31 %, 2022 +0,07 %, 2023 +0,25 %, 2024 −0,03 %, 2025 +0,48 %, 2026 −0,23 % je Trade.
- **Aktien-Indizes auf 1h** liegen am besten (Ø +0,29 %, t 1,8, S&P 500 allein t 2,8). Diese Auswahl ist aber im Nachhinein getroffen. Bei 19 Assets erwartet man rein zufällig etwa eines mit t über 2.
