import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api';
import { Blotter } from './components/Blotter';
import { ChartPanel } from './components/ChartPanel';
import { OrderTicket } from './components/OrderTicket';
import { Watchlist } from './components/Watchlist';
import { formatMoney, formatNumber, formatPercent, tone, unitLabel } from './format';
import type { Account, Candle, Overview, Quote, Unit } from './types';

const DEFAULT_WATCH = ['453', '451', '7836', '167', '462', '419', '703', '673', '2023'];

function readWatch(): string[] {
  try {
    const raw = localStorage.getItem('talar.watch');
    const parsed = raw ? (JSON.parse(raw) as string[]) : DEFAULT_WATCH;
    return parsed.length ? parsed : DEFAULT_WATCH;
  } catch {
    return DEFAULT_WATCH;
  }
}

export function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [selectedId, setSelectedId] = useState(() => localStorage.getItem('talar.symbol') || '453');
  const [quote, setQuote] = useState<Quote | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [candleNote, setCandleNote] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [searchRows, setSearchRows] = useState<Overview['symbols'] | null>(null);
  const [watchIds, setWatchIds] = useState<string[]>(readWatch);
  const [unit, setUnit] = useState<Unit>(() => (localStorage.getItem('talar.unit') === 'toman' ? 'toman' : 'rial'));
  const [view, setView] = useState<'chart' | 'map'>('chart');
  const [clock, setClock] = useState('--:--:--');
  const [bootError, setBootError] = useState<string | null>(null);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshOverview = useCallback(async () => {
    const data = await api.overview();
    setOverview(data);
    setAccount(data.account);
    setBootError(null);
    return data;
  }, []);

  useEffect(() => {
    let stop = false;
    refreshOverview().catch((error: Error) => {
      if (!stop) setBootError(error.message);
    });
    const timer = setInterval(() => {
      refreshOverview().catch(() => {});
    }, 20_000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [refreshOverview]);

  useEffect(() => {
    const timer = setInterval(() => {
      setClock(
        new Intl.DateTimeFormat('fa-IR', {
          timeZone: 'Asia/Tehran',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hourCycle: 'h23',
        }).format(new Date()),
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let stop = false;
    setCandleNote(null);
    api
      .quote(selectedId)
      .then((data) => {
        if (stop) return;
        setQuote(data.quote);
        setAccount(data.account);
      })
      .catch((error: Error) => {
        if (!stop) setQuote(null);
        if (!stop) setOrderError(error.message);
      });
    api
      .candles(selectedId)
      .then((data) => {
        if (stop) return;
        setCandles(data.candles);
        setCandleNote(data.candles.length ? null : 'برای این نماد کندل روزانه برنگشت.');
      })
      .catch(() => {
        if (!stop) {
          setCandles([]);
          setCandleNote('نمودار روزانه الان در دسترس نیست.');
        }
      });
    return () => {
      stop = true;
    };
  }, [selectedId]);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setSearchRows(null);
      return;
    }
    const timer = setTimeout(() => {
      api
        .search(q)
        .then((data) => setSearchRows(data.symbols))
        .catch(() => setSearchRows([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    localStorage.setItem('talar.watch', JSON.stringify(watchIds));
  }, [watchIds]);

  useEffect(() => {
    localStorage.setItem('talar.unit', unit);
  }, [unit]);

  const symbols = searchRows ?? overview?.symbols ?? [];
  const boardRow = useMemo(
    () => overview?.symbols.find((symbol) => symbol.id === selectedId) ?? null,
    [overview, selectedId],
  );
  const positionQty = account?.positions.find((position) => position.symbolId === selectedId)?.qty ?? 0;

  function selectSymbol(id: string) {
    setSelectedId(id);
    setOrderError(null);
    setView('chart');
    localStorage.setItem('talar.symbol', id);
  }

  async function submitOrder(order: { side: 'buy' | 'sell'; type: 'market' | 'limit'; qty: number; price?: number }) {
    setBusy(true);
    setOrderError(null);
    try {
      const next = await api.order({ ...order, symbolId: selectedId });
      setAccount(next);
    } catch (error) {
      setOrderError(error instanceof Error ? error.message : 'ثبت سفارش ناموفق بود');
    } finally {
      setBusy(false);
    }
  }

  async function cancelOrder(id: string) {
    try {
      setAccount(await api.cancel(id));
    } catch (error) {
      setOrderError(error instanceof Error ? error.message : 'لغو سفارش ناموفق بود');
    }
  }

  async function resetAccount() {
    setAccount(await api.reset());
  }

  const session = overview?.session;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="mark" aria-hidden="true" />
          <div>
            <strong>تالار</strong>
            <small>معاملات آزمایشی بورس تهران و فرابورس</small>
          </div>
        </div>
        <div className="indices">
          {(overview?.indices ?? []).map((index) => (
            <div key={index.id} className="index-chip">
              <span>{index.name}</span>
              <strong className="num">{formatNumber(index.value, 0)}</strong>
              <em className={tone(index.changePercent)}>{formatPercent(index.changePercent)}</em>
            </div>
          ))}
        </div>
        <div className="session">
          <span className={`pill ${session?.phase ?? 'closed'}`}>{session?.label ?? '…'}</span>
          <time className="num">{clock}</time>
          <small>تهران</small>
        </div>
        <div className="equity">
          <span>خالص حساب</span>
          <strong className={`num ${tone(account?.pnl)}`}>{account ? formatMoney(account.equity, unit) : '—'}</strong>
          <small className={tone(account?.pnl)}>
            {account ? `${formatMoney(account.pnl, unit)} ${unitLabel(unit)}` : ''}
          </small>
        </div>
        <button
          type="button"
          className="ghost"
          onClick={() => setUnit((current) => (current === 'rial' ? 'toman' : 'rial'))}
        >
          نمایش {unit === 'rial' ? 'تومان' : 'ریال'}
        </button>
      </header>

      {bootError ? <div className="banner bad">{bootError}</div> : null}
      {overview?.source === 'snapshot' ? (
        <div className="banner">اتصال زنده برقرار نیست و آخرین نمای ذخیره‌شده بازار نشان داده می‌شود.</div>
      ) : null}

      <div className="workspace">
        <Watchlist
          symbols={symbols}
          selectedId={selectedId}
          watchIds={watchIds}
          unit={unit}
          query={query}
          onQuery={setQuery}
          onSelect={selectSymbol}
          onToggleWatch={(id) =>
            setWatchIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
          }
        />
        <ChartPanel
          quote={quote}
          boardRow={boardRow}
          candles={candles}
          candleNote={candleNote}
          unit={unit}
          view={view}
          symbols={overview?.symbols ?? []}
          onView={setView}
          onSelect={selectSymbol}
        />
        <OrderTicket
          quote={quote}
          cash={account?.cash ?? 0}
          positionQty={positionQty}
          unit={unit}
          busy={busy}
          message={orderError}
          onSubmit={submitOrder}
        />
      </div>
      <Blotter account={account} unit={unit} onCancel={cancelOrder} onReset={resetAccount} onSelect={selectSymbol} />
    </div>
  );
}
