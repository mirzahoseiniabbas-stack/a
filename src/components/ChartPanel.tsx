import { useEffect, useRef } from 'react';
import { ColorType, CrosshairMode, createChart, type IChartApi, type ISeriesApi, type Time } from 'lightweight-charts';
import { formatCompact, formatMoney, formatNumber, formatPercent, heatColor, tone, unitLabel } from '../format';
import { treemap } from '../treemap';
import type { Candle, Quote, SymbolRow, Unit } from '../types';

function formatCandleTick(time: Time): string {
  const iso =
    typeof time === 'string'
      ? time
      : typeof time === 'number'
        ? new Date(time * 1000).toISOString().slice(0, 10)
        : `${time.year}-${String(time.month).padStart(2, '0')}-${String(time.day).padStart(2, '0')}`;
  return new Intl.DateTimeFormat('fa-IR', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${iso}T12:00:00Z`));
}

interface Props {
  quote: Quote | null;
  boardRow: SymbolRow | null;
  candles: Candle[];
  candleNote: string | null;
  unit: Unit;
  view: 'chart' | 'map';
  symbols: SymbolRow[];
  onView: (view: 'chart' | 'map') => void;
  onSelect: (id: string) => void;
}

export function ChartPanel({ quote, boardRow, candles, candleNote, unit, view, symbols, onView, onSelect }: Props) {
  const symbol = quote?.symbol || boardRow?.symbol || '—';
  const name = quote?.name || boardRow?.name || '';
  const last = quote?.last || boardRow?.last || 0;
  const change = quote?.change ?? boardRow?.change ?? 0;
  const changePercent = quote?.changePercent ?? boardRow?.changePercent ?? 0;

  return (
    <section className="panel chart-panel">
      <div className="symbol-head">
        <div>
          <div className="symbol-title">
            <h2>{symbol}</h2>
            <span className="muted">{name}</span>
          </div>
          <div className="last-line">
            <strong className={`num last ${tone(change)}`}>{last ? formatMoney(last, unit) : '—'}</strong>
            <span className={tone(change)}>
              {formatMoney(change, unit)} ({formatPercent(changePercent)})
            </span>
            <span className="unit-tag">{unitLabel(unit)}</span>
          </div>
        </div>
        <div className="view-switch">
          <button type="button" className={view === 'chart' ? 'on' : ''} onClick={() => onView('chart')}>
            نمودار
          </button>
          <button type="button" className={view === 'map' ? 'on' : ''} onClick={() => onView('map')}>
            نقشه بازار
          </button>
        </div>
      </div>

      {view === 'chart' ? (
        <>
          <Stats quote={quote} unit={unit} />
          <CandleChart candles={candles} note={candleNote} />
        </>
      ) : (
        <MarketMap symbols={symbols} onSelect={onSelect} unit={unit} />
      )}
    </section>
  );
}

function Stats({ quote, unit }: { quote: Quote | null; unit: Unit }) {
  if (!quote) return <div className="stats muted">در حال دریافت جزئیات نماد…</div>;
  const real = quote.realBuyVolume + quote.realSellVolume;
  const legal = quote.legalBuyVolume + quote.legalSellVolume;
  const flow = real + legal;
  return (
    <div className="stats">
      <Stat label="پایانی" value={formatMoney(quote.close, unit)} />
      <Stat label="اول" value={formatMoney(quote.open, unit)} />
      <Stat label="بیشترین" value={formatMoney(quote.high, unit)} />
      <Stat label="کمترین" value={formatMoney(quote.low, unit)} />
      <Stat label="دیروز" value={formatMoney(quote.prev, unit)} />
      <Stat label="حجم" value={formatCompact(quote.volume, 'rial')} />
      <Stat label="ارزش" value={formatCompact(quote.value, unit)} />
      <Stat label="معاملات" value={quote.trades ? quote.trades.toLocaleString('fa-IR') : '—'} />
      <Stat label="قدرت خریدار" value={quote.buyPower == null ? '—' : formatNumber(quote.buyPower, 2)} />
      <div className="flow">
        <span>حقیقی / حقوقی</span>
        <div className="flow-bar" title="سهم حجم حقیقی و حقوقی">
          <i style={{ width: flow ? `${(real / flow) * 100}%` : '0%' }} />
        </div>
        <small className="muted">{flow ? `${Math.round((real / flow) * 100).toLocaleString('fa-IR')}٪ حقیقی` : '—'}</small>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong className="num">{value}</strong>
    </div>
  );
}

function CandleChart({ candles, note }: { candles: Candle[]; note: string | null }) {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<{
    chart: IChartApi;
    series: ISeriesApi<'Candlestick'>;
    volume: ISeriesApi<'Histogram'>;
  } | null>(null);

  useEffect(() => {
    if (!host.current) return;
    const chart = createChart(host.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#93a4b8',
        fontFamily: 'Vazirmatn, Tahoma, sans-serif',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)' },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.08)',
        fixRightEdge: true,
        tickMarkFormatter: (time: Time) => formatCandleTick(time),
      },
      crosshair: { mode: CrosshairMode.Normal },
      localization: { locale: 'fa-IR' },
      handleScroll: true,
      handleScale: true,
    });
    const series = chart.addCandlestickSeries({
      upColor: '#1fbf75',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#1fbf75',
      wickDownColor: '#ef5350',
    });
    const volume = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    const resize = () => {
      if (!host.current) return;
      chart.applyOptions({ width: host.current.clientWidth, height: host.current.clientHeight });
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(host.current);
    api.current = { chart, series, volume };
    return () => {
      observer.disconnect();
      chart.remove();
      api.current = null;
    };
  }, []);

  useEffect(() => {
    const handle = api.current;
    if (!handle) return;
    handle.series.setData(
      candles.map((candle) => ({
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    );
    handle.volume.setData(
      candles.map((candle) => ({
        time: candle.time,
        value: candle.volume,
        color: candle.close >= candle.open ? 'rgba(31,191,117,0.45)' : 'rgba(239,83,80,0.45)',
      })),
    );
    if (candles.length) handle.chart.timeScale().fitContent();
  }, [candles]);

  return (
    <div className="chart-wrap">
      <div ref={host} className="chart" />
      {!candles.length ? <p className="chart-note">{note || 'نمودار روزانه در دسترس نیست.'}</p> : null}
    </div>
  );
}

function MarketMap({ symbols, onSelect, unit }: { symbols: SymbolRow[]; onSelect: (id: string) => void; unit: Unit }) {
  const groups = new Map<string, SymbolRow[]>();
  for (const symbol of symbols) {
    if (!symbol.value || !symbol.last) continue;
    const list = groups.get(symbol.sector) ?? [];
    list.push(symbol);
    groups.set(symbol.sector, list);
  }
  const nodes = [...groups.entries()]
    .map(([sector, rows]) => ({
      id: sector,
      label: sector,
      value: rows.reduce((sum, row) => sum + row.value, 0),
      children: rows.map((row) => ({
        id: row.id,
        label: row.symbol,
        value: row.value,
        changePercent: row.changePercent,
        last: row.last,
        name: row.name,
      })),
    }))
    .sort((a, b) => b.value - a.value);

  const rects = treemap(nodes);

  return (
    <div className="map">
      {rects.map((rect) => {
        const change = 'changePercent' in rect ? Number(rect.changePercent) : 0;
        const last = 'last' in rect ? Number(rect.last) : 0;
        const name = 'name' in rect ? String(rect.name) : rect.label;
        return (
          <button
            key={rect.id}
            type="button"
            className="tile"
            style={{
              insetInlineStart: `${rect.x}%`,
              top: `${rect.y}%`,
              width: `${rect.w}%`,
              height: `${rect.h}%`,
              background: heatColor(change),
            }}
            title={`${name} ${formatMoney(last, unit)} ${formatPercent(change)}`}
            onClick={() => onSelect(rect.id)}
          >
            {rect.w > 4.2 && rect.h > 7 ? <strong>{rect.label}</strong> : null}
            {rect.w > 6 && rect.h > 12 ? <small>{formatPercent(change)}</small> : null}
          </button>
        );
      })}
    </div>
  );
}
