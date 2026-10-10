import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { tickSize } from './fees.mjs';

const BASE = 'https://rahavard365.com/api/v2';
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SNAPSHOT_PATH = path.join(ROOT, 'snapshot.json');

const INDEXES = [
  { id: '1', name: 'شاخص کل' },
  { id: '57', name: 'شاخص کل هم‌وزن' },
  { id: '60', name: 'شاخص کل فرابورس' },
];

export function symbolsFromMap(payload) {
  const root = payload?.data?.[0]?.root;
  if (!root) return [];
  const symbols = [];
  const add = (node, sector) => {
    const last = Number(node.real_close_price) || 0;
    const ratio = Number(node.value) || 0;
    const prev = ratio === -1 ? last : last / (1 + ratio);
    symbols.push({
      id: String(node.id),
      symbol: node.name || '',
      name: node.fullname || node.name || '',
      sector: sector || 'سایر',
      last,
      change: last ? Math.round(last - prev) : 0,
      changePercent: Math.round(ratio * 10000) / 100,
      value: Number(node.area) || 0,
    });
  };
  const walk = (node, sector) => {
    const kids = node.children || [];
    if (!kids.length) return;
    const branches = kids.filter((child) => child.children?.length);
    const leaves = kids.filter((child) => !child.children?.length);
    if (branches.length) {
      for (const leaf of leaves) add(leaf, sector);
      for (const branch of branches) {
        walk(branch, branch.fullname || branch.name || sector);
      }
      return;
    }
    const sec = node.id === 'root' ? sector : node.fullname || node.name || sector;
    for (const leaf of leaves) add(leaf, sec);
  };
  walk(root, 'بازار');
  return symbols;
}

function normalizeIndex(meta, payload) {
  const data = payload?.data ?? {};
  const ratio = Number(data.close_value_change_percent) || 0;
  return {
    id: meta.id,
    name: meta.name,
    value: Number(data.close_value) || 0,
    change: Number(data.close_value_change) || 0,
    changePercent: Math.round(ratio * 10000) / 100,
    asOf: data.end_date_time || null,
  };
}

function quoteFromParts(row, header, trade) {
  const asset = header?.data?.asset ?? {};
  const t = trade?.data ?? {};
  const last = Number(t.real_close_price ?? row?.last ?? 0);
  const close = Number(t.close_price ?? last);
  const change = Number(t.real_close_price_change ?? row?.change ?? 0);
  const ratio = t.real_close_price_change_percent;
  const changePercent =
    ratio == null ? row?.changePercent ?? 0 : Math.round(Number(ratio) * 10000) / 100;
  const prev = last && change ? last - change : row ? row.last - row.change : last;
  const personBuy = Number(t.person_buy_per_head) || 0;
  const personSell = Number(t.person_sell_per_head) || 0;
  return {
    id: String(asset.id || row?.id || t.id),
    symbol: asset.trade_symbol || row?.symbol || '',
    name: asset.name || row?.name || '',
    english: asset.english_trade_symbol || '',
    sector: asset.category?.parent?.name || row?.sector || '',
    exchange: asset.exchange?.title || '',
    state: asset.instrument_state?.state || null,
    last,
    close,
    change,
    changePercent,
    open: Number(t.open_price) || last,
    high: Number(t.high_price) || last,
    low: Number(t.low_price) || last,
    prev,
    volume: Number(t.volume) || 0,
    value: Number(t.value) || row?.value || 0,
    trades: Number(t.trade_count) || 0,
    buyers: Number(t.buyer_count) || 0,
    buyPower: personSell ? personBuy / personSell : null,
    realBuyVolume: Number(t.person_buy_volume) || 0,
    realSellVolume: Number(t.person_sell_volume) || 0,
    legalBuyVolume: Number(t.company_buy_volume) || 0,
    legalSellVolume: Number(t.company_sell_volume) || 0,
    tick: tickSize(last || 1),
    asOf: t.end_time || null,
    source: trade ? 'live' : 'board',
  };
}

async function fetchJson(pathname) {
  const response = await fetch(`${BASE}${pathname}`, {
    headers: {
      Accept: 'application/json',
      'User-Agent': 'TalarPaper/1.0',
    },
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) {
    throw new Error(`market ${response.status}`);
  }
  return response.json();
}

export function createMarket() {
  const cache = {
    at: 0,
    source: 'snapshot',
    asOf: null,
    note: '',
    indices: [],
    symbols: [],
    quotes: new Map(),
    candles: new Map(),
    error: null,
  };

  async function loadSnapshot() {
    const raw = JSON.parse(await readFile(SNAPSHOT_PATH, 'utf8'));
    cache.indices = raw.indices ?? [];
    cache.symbols = raw.symbols ?? [];
    cache.asOf = raw.asOf ?? null;
    cache.note = raw.note ?? '';
    cache.source = 'snapshot';
  }

  async function refreshBoard() {
    if (cache.symbols.length && Date.now() - cache.at < 20_000) return;
    try {
      const [map, ...indexes] = await Promise.all([
        fetchJson('/marketmap/data?category_id=1&coloring_type_id=1&size_type_id=1'),
        ...INDEXES.map((index) => fetchJson(`/market-data/indexes/${index.id}/last-value`)),
      ]);
      const symbols = symbolsFromMap(map);
      if (symbols.length < 100) throw new Error('board too small');
      cache.symbols = symbols;
      cache.indices = INDEXES.map((meta, i) => normalizeIndex(meta, indexes[i]));
      cache.asOf = cache.indices[0]?.asOf ?? new Date().toISOString();
      cache.source = 'live';
      cache.note = 'داده عمومی بازار';
      cache.error = null;
    } catch (error) {
      cache.error = error instanceof Error ? error.message : String(error);
      if (!cache.symbols.length) await loadSnapshot();
    } finally {
      cache.at = Date.now();
    }
  }

  async function board() {
    if (!cache.symbols.length) await loadSnapshot();
    await refreshBoard();
    return {
      source: cache.source,
      asOf: cache.asOf,
      note: cache.note,
      error: cache.error,
      indices: cache.indices,
      symbols: cache.symbols,
    };
  }

  function prices() {
    const map = new Map();
    for (const symbol of cache.symbols) {
      if (symbol.last) map.set(symbol.id, symbol.last);
    }
    for (const [id, entry] of cache.quotes) {
      if (entry.data?.last) map.set(id, entry.data.last);
    }
    return map;
  }

  async function quote(id) {
    const hit = cache.quotes.get(id);
    if (hit && Date.now() - hit.at < 15_000) return hit.data;
    const row = cache.symbols.find((symbol) => symbol.id === id);
    try {
      const [header, trade] = await Promise.all([
        fetchJson(`/asset/${encodeURIComponent(id)}/header`),
        fetchJson(`/market-data/assets/${encodeURIComponent(id)}/last-trade`),
      ]);
      const data = quoteFromParts(row, header, trade);
      cache.quotes.set(id, { at: Date.now(), data });
      return data;
    } catch (error) {
      if (row?.last) {
        const data = quoteFromParts(row, null, null);
        data.source = cache.source;
        return data;
      }
      if (hit) return hit.data;
      const wrapped = new Error('نماد پیدا نشد');
      wrapped.status = 404;
      wrapped.cause = error;
      throw wrapped;
    }
  }

  async function candles(id) {
    const hit = cache.candles.get(id);
    if (hit && Date.now() - hit.at < 10 * 60_000) return hit.data;
    const raw = await fetchJson(
      `/chart/light-bars?symbol=${encodeURIComponent(`exchange.asset:${id}:close`)}`,
    );
    const byDay = new Map();
    for (const bar of raw.data ?? []) {
      const time = String(bar.utc ?? '').slice(0, 10);
      if (!time || !bar.close) continue;
      byDay.set(time, {
        time,
        open: Math.round(Number(bar.open) * 100) / 100,
        high: Math.round(Number(bar.high) * 100) / 100,
        low: Math.round(Number(bar.low) * 100) / 100,
        close: Math.round(Number(bar.close) * 100) / 100,
        volume: Number(bar.volume) || 0,
      });
    }
    const list = [...byDay.values()].sort((a, b) => a.time.localeCompare(b.time));
    cache.candles.set(id, { at: Date.now(), data: list });
    return list;
  }

  async function search(query) {
    const q = query.trim();
    const local = cache.symbols
      .filter((symbol) => !q || symbol.symbol.includes(q) || symbol.name.includes(q))
      .slice(0, 40);
    if (!q || local.length >= 8) return local;
    try {
      const remote = await fetchJson(`/search?keyword=${encodeURIComponent(q)}`);
      const seen = new Set(local.map((symbol) => symbol.id));
      for (const item of remote.data ?? []) {
        if (item.entity_type !== 'exchange.asset') continue;
        if (!['1', '2', '7'].includes(String(item.type_id))) continue;
        const id = String(item.entity_id);
        if (seen.has(id)) continue;
        seen.add(id);
        local.push({
          id,
          symbol: item.trade_symbol || item.short_name || '',
          name: item.name || '',
          sector: item.type || '',
          last: 0,
          change: 0,
          changePercent: 0,
          value: 0,
        });
        if (local.length >= 40) break;
      }
    } catch {
      /* local results still stand */
    }
    return local;
  }

  return { board, quote, candles, search, prices, loadSnapshot };
}
