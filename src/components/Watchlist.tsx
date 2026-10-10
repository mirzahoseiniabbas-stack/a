import { useMemo, useState } from 'react';
import { formatMoney, formatPercent, tone } from '../format';
import type { SymbolRow, Unit } from '../types';

type Mode = 'all' | 'watch' | 'value' | 'gainers' | 'losers';

const MODES: { id: Mode; label: string }[] = [
  { id: 'watch', label: 'دیده‌بان' },
  { id: 'value', label: 'ارزش' },
  { id: 'gainers', label: 'رشد' },
  { id: 'losers', label: 'افت' },
  { id: 'all', label: 'همه' },
];

interface Props {
  symbols: SymbolRow[];
  selectedId: string;
  watchIds: string[];
  unit: Unit;
  query: string;
  onQuery: (value: string) => void;
  onSelect: (id: string) => void;
  onToggleWatch: (id: string) => void;
}

export function Watchlist({
  symbols,
  selectedId,
  watchIds,
  unit,
  query,
  onQuery,
  onSelect,
  onToggleWatch,
}: Props) {
  const [mode, setMode] = useState<Mode>('watch');
  const watch = useMemo(() => new Set(watchIds), [watchIds]);

  const rows = useMemo(() => {
    if (query.trim()) return symbols;
    if (mode === 'watch') {
      const order = new Map(watchIds.map((id, index) => [id, index]));
      return symbols
        .filter((symbol) => watch.has(symbol.id))
        .sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0));
    }
    if (mode === 'value') return [...symbols].sort((a, b) => b.value - a.value).slice(0, 40);
    if (mode === 'gainers') return [...symbols].sort((a, b) => b.changePercent - a.changePercent).slice(0, 30);
    if (mode === 'losers') return [...symbols].sort((a, b) => a.changePercent - b.changePercent).slice(0, 30);
    return [...symbols].sort((a, b) => a.symbol.localeCompare(b.symbol, 'fa'));
  }, [symbols, mode, query, watch, watchIds]);

  return (
    <aside className="panel watchlist">
      <div className="panel-head">
        <h2>نمادها</h2>
        <span className="muted">{rows.length.toLocaleString('fa-IR')}</span>
      </div>
      <label className="search">
        <span className="sr">جستجوی نماد</span>
        <input
          value={query}
          onChange={(event) => onQuery(event.target.value)}
          placeholder="نام یا نماد، مثلاً فولاد"
        />
      </label>
      <div className="modes" role="tablist">
        {MODES.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={mode === item.id}
            className={mode === item.id ? 'on' : ''}
            onClick={() => setMode(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="rows">
        {rows.length === 0 ? <p className="empty">نمادی در این فهرست نیست.</p> : null}
        {rows.map((symbol) => (
          <div key={symbol.id} className={symbol.id === selectedId ? 'row selected' : 'row'}>
            <button type="button" className="row-main" onClick={() => onSelect(symbol.id)}>
              <span className="sym">
                <strong>{symbol.symbol}</strong>
                <small>{symbol.name}</small>
              </span>
              <span className="px">
                <strong className="num">{symbol.last ? formatMoney(symbol.last, unit) : '—'}</strong>
                <small className={tone(symbol.changePercent)}>{formatPercent(symbol.changePercent)}</small>
              </span>
            </button>
            <button
              type="button"
              className={watch.has(symbol.id) ? 'star on' : 'star'}
              aria-label={watch.has(symbol.id) ? 'حذف از دیده‌بان' : 'افزودن به دیده‌بان'}
              onClick={() => onToggleWatch(symbol.id)}
            >
              ★
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
