import { useState } from 'react';
import { formatClock, formatMoney, formatPercent, tone } from '../format';
import type { Account, Unit } from '../types';

interface Props {
  account: Account | null;
  unit: Unit;
  onCancel: (id: string) => void;
  onReset: () => void;
  onSelect: (id: string) => void;
}

const TABS = [
  { id: 'positions', label: 'پورتفوی' },
  { id: 'orders', label: 'سفارش‌ها' },
  { id: 'trades', label: 'معاملات' },
] as const;

export function Blotter({ account, unit, onCancel, onReset, onSelect }: Props) {
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('positions');
  const [armed, setArmed] = useState(false);

  return (
    <section className="panel blotter">
      <div className="blotter-head">
        <div className="modes" role="tablist">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              className={tab === item.id ? 'on' : ''}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="ghost danger"
          onClick={() => {
            if (!armed) {
              setArmed(true);
              return;
            }
            setArmed(false);
            onReset();
          }}
          onBlur={() => setArmed(false)}
        >
          {armed ? 'تأیید بازنشانی حساب' : 'بازنشانی حساب آزمایشی'}
        </button>
      </div>
      <div className="table-wrap">
        {tab === 'positions' ? <Positions account={account} unit={unit} onSelect={onSelect} /> : null}
        {tab === 'orders' ? <Orders account={account} unit={unit} onCancel={onCancel} onSelect={onSelect} /> : null}
        {tab === 'trades' ? <Trades account={account} unit={unit} onSelect={onSelect} /> : null}
      </div>
    </section>
  );
}

function Positions({ account, unit, onSelect }: { account: Account | null; unit: Unit; onSelect: (id: string) => void }) {
  if (!account?.positions.length) return <p className="empty">هنوز سهمی در پورتفوی آزمایشی نیست.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>نماد</th>
          <th>تعداد</th>
          <th>میانگین</th>
          <th>آخرین</th>
          <th>ارزش</th>
          <th>سود/زیان</th>
          <th>پس از کارمزد فروش</th>
        </tr>
      </thead>
      <tbody>
        {account.positions.map((position) => (
          <tr key={position.symbolId}>
            <td>
              <button type="button" className="link" onClick={() => onSelect(position.symbolId)}>
                {position.symbol}
              </button>
              <small>{position.name}</small>
            </td>
            <td className="num">{position.qty.toLocaleString('fa-IR')}</td>
            <td className="num">{formatMoney(position.avgCost, unit)}</td>
            <td className="num">{position.last == null ? '—' : formatMoney(position.last, unit)}</td>
            <td className="num">{position.marketValue == null ? '—' : formatMoney(position.marketValue, unit)}</td>
            <td className={`num ${tone(position.pnl)}`}>
              {position.pnl == null ? '—' : `${formatMoney(position.pnl, unit)} (${formatPercent(position.pnlPercent)})`}
            </td>
            <td className={`num ${tone(position.exitPnl)}`}>
              {position.exitPnl == null ? '—' : formatMoney(position.exitPnl, unit)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Orders({
  account,
  unit,
  onCancel,
  onSelect,
}: {
  account: Account | null;
  unit: Unit;
  onCancel: (id: string) => void;
  onSelect: (id: string) => void;
}) {
  if (!account?.orders.length) return <p className="empty">سفارشی ثبت نشده است.</p>;
  const statusLabel = {
    open: 'باز',
    filled: 'اجراشده',
    cancelled: 'لغوشده',
    rejected: 'ردشده',
  };
  return (
    <table>
      <thead>
        <tr>
          <th>زمان</th>
          <th>نماد</th>
          <th>سمت</th>
          <th>نوع</th>
          <th>حجم</th>
          <th>قیمت</th>
          <th>وضعیت</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {account.orders.map((order) => (
          <tr key={order.id}>
            <td>{formatClock(order.createdAt)}</td>
            <td>
              <button type="button" className="link" onClick={() => onSelect(order.symbolId)}>
                {order.symbol}
              </button>
            </td>
            <td className={order.side === 'buy' ? 'up' : 'down'}>{order.side === 'buy' ? 'خرید' : 'فروش'}</td>
            <td>{order.type === 'market' ? 'بازار' : 'محدود'}</td>
            <td className="num">{order.qty.toLocaleString('fa-IR')}</td>
            <td className="num">{formatMoney(order.fillPrice ?? order.price, unit)}</td>
            <td>
              {statusLabel[order.status]}
              {order.message ? <small>{order.message}</small> : null}
            </td>
            <td>
              {order.status === 'open' ? (
                <button type="button" className="ghost" onClick={() => onCancel(order.id)}>
                  لغو
                </button>
              ) : null}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Trades({ account, unit, onSelect }: { account: Account | null; unit: Unit; onSelect: (id: string) => void }) {
  if (!account?.trades.length) return <p className="empty">معامله‌ای انجام نشده است.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>زمان</th>
          <th>نماد</th>
          <th>سمت</th>
          <th>حجم</th>
          <th>قیمت</th>
          <th>کارمزد</th>
        </tr>
      </thead>
      <tbody>
        {account.trades.map((trade) => (
          <tr key={trade.id}>
            <td>{formatClock(trade.time)}</td>
            <td>
              <button type="button" className="link" onClick={() => onSelect(trade.symbolId)}>
                {trade.symbol}
              </button>
            </td>
            <td className={trade.side === 'buy' ? 'up' : 'down'}>{trade.side === 'buy' ? 'خرید' : 'فروش'}</td>
            <td className="num">{trade.qty.toLocaleString('fa-IR')}</td>
            <td className="num">{formatMoney(trade.price, unit)}</td>
            <td className="num">{formatMoney(trade.fee, unit)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
