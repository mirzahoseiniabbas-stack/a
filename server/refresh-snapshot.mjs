import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { symbolsFromMap } from './market.mjs';

const BASE = 'https://rahavard365.com/api/v2';
const dest = path.join(path.dirname(fileURLToPath(import.meta.url)), 'snapshot.json');

async function get(pathname) {
  const response = await fetch(`${BASE}${pathname}`, {
    headers: { Accept: 'application/json', 'User-Agent': 'TalarPaper/1.0' },
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) throw new Error(`${pathname} ${response.status}`);
  return response.json();
}

const indexes = [
  { id: '1', name: 'شاخص کل' },
  { id: '57', name: 'شاخص کل هم‌وزن' },
  { id: '60', name: 'شاخص کل فرابورس' },
];

const [map, ...rawIndexes] = await Promise.all([
  get('/marketmap/data?category_id=1&coloring_type_id=1&size_type_id=1'),
  ...indexes.map((index) => get(`/market-data/indexes/${index.id}/last-value`)),
]);

const symbols = symbolsFromMap(map);
if (symbols.length < 100) throw new Error(`unexpected symbol count ${symbols.length}`);

const normalized = rawIndexes.map((payload, i) => {
  const data = payload.data ?? {};
  return {
    id: indexes[i].id,
    name: indexes[i].name,
    value: data.close_value,
    change: data.close_value_change,
    changePercent: Math.round((data.close_value_change_percent || 0) * 10000) / 100,
    asOf: data.end_date_time,
  };
});

const snapshot = {
  source: 'snapshot',
  asOf: normalized[0]?.asOf ?? null,
  note: 'نمای ذخیره‌شده از داده عمومی بازار برای وقتی که اتصال زنده قطع است.',
  indices: normalized,
  symbols,
};

await writeFile(dest, JSON.stringify(snapshot));
console.log(`wrote ${symbols.length} symbols to ${dest}`);
