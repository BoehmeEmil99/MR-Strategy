// Lädt 15-Minuten-Kerzen (Bid) eines Instruments von Dukascopy als CSV.
// Aufruf: node fetch/dl.mjs <instrument> <von YYYY-MM-DD> <bis YYYY-MM-DD> <ausgabe.csv>
import { writeFileSync } from "node:fs";
import { getHistoricalRates } from "dukascopy-node";

const [instrument, from, to, out] = process.argv.slice(2);

const rows = await getHistoricalRates({
  instrument,
  dates: { from: new Date(from), to: new Date(to) },
  timeframe: "m15",
  priceType: "bid",
  format: "array",
  volumes: false,
  ignoreFlats: true,
  batchSize: 10,
  pauseBetweenBatchesMs: 500,
  retryCount: 5,
  pauseBetweenRetriesMs: 2000,
  retryOnEmpty: true,
  failAfterRetryCount: true,
});

const lines = ["ts,open,high,low,close"];
for (const r of rows) lines.push(r.slice(0, 5).join(","));
writeFileSync(out, lines.join("\n") + "\n");
console.log(`${instrument} ${from}..${to}: ${rows.length} Kerzen`);
