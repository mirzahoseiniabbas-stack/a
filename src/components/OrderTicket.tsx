import { useEffect, useMemo, useState } from 'react';
import { BUY_PREVIEW, SELL_PREVIEW, maxBuyQty } from '../fees';
import { formatMoney, formatNumber, parseNumber } from '../format';
import type { Quote, Unit } from '../types';

interface Props {
  quote: Quote | null;
  cash: number;
  positionQty: number;
  unit: Unit;
  busy: boolean;
  message: string | null;
  onSubmit: (order: { side: 'buy' | 'sell'; type: 'market' | 'limit'; qty: number; price?: number }) => void;
}

export function OrderTicket({ quote, cash, positionQty, unit, busy, message, onSubmit }: Props) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [type, setType] = useState<'market' | 'limit'>('limit');
  const [qtyText, setQtyText] = useState('1000');
  const [priceText, setPriceText] = useState('');

  useEffect(() => {
    if (quote?.last) setPriceText(String(quote.last));
  }, [quote?.id, quote?.last]);

  const qty = parseNumber(qtyText);
  const price = type === 'market' ? quote?.last ?? Number.NaN : parseNumber(priceText);
  const preview = useMemo(() => {
    if (!quote || !Number.isInteger(qty) || qty <= 0 || !Number.isFinite(price) || price <= 0) return null;
    return side === 'buy' ? BUY_PREVIEW(qty, price) : SELL_PREVIEW(qty, price);
  }, [quote, qty, price, side]);

  const capacity = quote && Number.isFinite(price) && price > 0 ? maxBuyQty(cash, price) : 0;

  function applyFraction(fraction: number) {
    if (side === 'sell') {
      setQtyText(String(Math.floor(positionQty * fraction)));
      return;
    }
    setQtyText(String(Math.floor(capacity * fraction)));
  }

  function submit() {
    if (!quote) return;
    onSubmit({
      side,
      type,
      qty,
      price: type === 'limit' ? price : undefined,
    });
  }

  return (
    <aside className="panel ticket">
      <div className="panel-head">
        <h2>سفارش آزمایشی</h2>
      </div>
      <p className="disclaimer">این سفارش فقط در حساب مجازی ثبت می‌شود و به هسته معاملات بورس ارسال نمی‌شود.</p>
      <div className="side-switch">
        <button type="button" className={side === 'buy' ? 'buy on' : 'buy'} onClick={() => setSide('buy')}>
          خرید
        </button>
        <button type="button" className={side === 'sell' ? 'sell on' : 'sell'} onClick={() => setSide('sell')}>
          فروش
        </button>
      </div>
      <div className="type-switch">
        <button type="button" className={type === 'limit' ? 'on' : ''} onClick={() => setType('limit')}>
          محدود
        </button>
        <button type="button" className={type === 'market' ? 'on' : ''} onClick={() => setType('market')}>
          بازار
        </button>
      </div>
      <label>
        حجم (سهم)
        <input inputMode="numeric" value={qtyText} onChange={(event) => setQtyText(event.target.value)} />
      </label>
      <label>
        قیمت (ریال)
        <input
          inputMode="numeric"
          value={type === 'market' ? (quote ? formatNumber(quote.last) : '') : priceText}
          disabled={type === 'market'}
          onChange={(event) => setPriceText(event.target.value)}
        />
      </label>
      {unit === 'toman' && Number.isFinite(price) && price > 0 ? (
        <p className="hint">معادل {formatMoney(price, 'toman')} تومان. سفارش همیشه با قیمت ریالی تابلو ثبت می‌شود.</p>
      ) : null}
      <div className="fractions">
        {[0.25, 0.5, 1].map((fraction) => (
          <button key={fraction} type="button" onClick={() => applyFraction(fraction)}>
            {fraction === 1 ? 'همه' : `${fraction * 100}٪`}
          </button>
        ))}
      </div>
      <dl className="preview">
        <div>
          <dt>نقد آزاد</dt>
          <dd className="num">{formatMoney(cash, unit)}</dd>
        </div>
        <div>
          <dt>مانده سهم</dt>
          <dd className="num">{positionQty.toLocaleString('fa-IR')}</dd>
        </div>
        <div>
          <dt>مبلغ ناخالص</dt>
          <dd className="num">{preview ? formatMoney(preview.gross, unit) : '—'}</dd>
        </div>
        <div>
          <dt>کارمزد {side === 'buy' ? 'خرید' : 'فروش'}</dt>
          <dd className="num">{preview ? formatMoney(preview.fee, unit) : '—'}</dd>
        </div>
        <div>
          <dt>{side === 'buy' ? 'بدهکار' : 'خالص دریافتی'}</dt>
          <dd className="num">{preview ? formatMoney(preview.total, unit) : '—'}</dd>
        </div>
      </dl>
      {quote ? <p className="hint">تیک قیمت این نماد {quote.tick.toLocaleString('fa-IR')} ریال است.</p> : null}
      {message ? <p className="form-error">{message}</p> : null}
      <button
        type="button"
        className={`submit ${side}`}
        disabled={busy || !quote?.last}
        onClick={submit}
      >
        {busy ? 'در حال ثبت…' : side === 'buy' ? `خرید ${quote?.symbol ?? ''}` : `فروش ${quote?.symbol ?? ''}`}
      </button>
    </aside>
  );
}
