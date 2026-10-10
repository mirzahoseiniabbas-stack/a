import { randomBytes } from 'node:crypto';
import { buyCost, sellProceeds, tickSize } from './fees.mjs';

export const STARTING_CASH = 5_000_000_000;

export function emptyAccount() {
  return {
    version: 1,
    startingCash: STARTING_CASH,
    cash: STARTING_CASH,
    positions: {},
    orders: [],
    trades: [],
  };
}

function id(prefix) {
  return `${prefix}_${Date.now().toString(36)}_${randomBytes(3).toString('hex')}`;
}

function fail(message) {
  const error = new Error(message);
  error.status = 400;
  return error;
}

export function createBroker(store) {
  function present(account, prices) {
    const positions = Object.values(account.positions).map((pos) => {
      const last = prices.get(pos.symbolId) ?? null;
      const marketValue = last == null ? null : pos.qty * last;
      const pnl = marketValue == null ? null : marketValue - pos.cost;
      const exit = last == null ? null : sellProceeds(pos.qty, last).total - pos.cost;
      return {
        symbolId: pos.symbolId,
        symbol: pos.symbol,
        name: pos.name,
        qty: pos.qty,
        avgCost: pos.qty ? Math.round(pos.cost / pos.qty) : 0,
        cost: pos.cost,
        last,
        marketValue,
        pnl,
        pnlPercent: pos.cost ? ((pnl ?? 0) / pos.cost) * 100 : 0,
        exitPnl: exit,
      };
    });
    positions.sort((a, b) => (b.marketValue ?? 0) - (a.marketValue ?? 0));
    const stockValue = positions.reduce((sum, p) => sum + (p.marketValue ?? p.cost), 0);
    const equity = account.cash + stockValue;
    return {
      cash: account.cash,
      startingCash: account.startingCash,
      positions,
      orders: [...account.orders].sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1)),
      trades: [...account.trades].sort((a, b) => (a.time < b.time ? 1 : -1)).slice(0, 100),
      stockValue,
      equity,
      pnl: equity - account.startingCash,
    };
  }

  async function view(prices = new Map()) {
    const account = await store.read();
    return present(account, prices);
  }

  function crosses(order, last) {
    if (order.type === 'market') return true;
    if (order.side === 'buy') return last <= order.price;
    return last >= order.price;
  }

  function fill(account, order, last, now) {
    const price = last;
    if (order.side === 'buy') {
      const cost = buyCost(order.qty, price);
      if (cost.total > account.cash) {
        order.status = 'rejected';
        order.message = 'موجودی نقد برای اجرای سفارش کافی نیست';
        order.updatedAt = now;
        return;
      }
      account.cash -= cost.total;
      const pos = account.positions[order.symbolId] ?? {
        symbolId: order.symbolId,
        symbol: order.symbol,
        name: order.name,
        qty: 0,
        cost: 0,
      };
      pos.qty += order.qty;
      pos.cost += cost.total;
      pos.symbol = order.symbol;
      pos.name = order.name;
      account.positions[order.symbolId] = pos;
      account.trades.push({
        id: id('trd'),
        orderId: order.id,
        symbolId: order.symbolId,
        symbol: order.symbol,
        name: order.name,
        side: 'buy',
        qty: order.qty,
        price,
        fee: cost.fee,
        gross: cost.gross,
        time: now,
      });
    } else {
      const pos = account.positions[order.symbolId];
      if (!pos || pos.qty < order.qty) {
        order.status = 'rejected';
        order.message = 'تعداد سهم برای فروش کافی نیست';
        order.updatedAt = now;
        return;
      }
      const proceeds = sellProceeds(order.qty, price);
      const released = Math.round((pos.cost * order.qty) / pos.qty);
      pos.qty -= order.qty;
      pos.cost -= released;
      if (pos.qty === 0) delete account.positions[order.symbolId];
      account.cash += proceeds.total;
      account.trades.push({
        id: id('trd'),
        orderId: order.id,
        symbolId: order.symbolId,
        symbol: order.symbol,
        name: order.name,
        side: 'sell',
        qty: order.qty,
        price,
        fee: proceeds.fee,
        gross: proceeds.gross,
        time: now,
      });
    }
    order.status = 'filled';
    order.fillPrice = price;
    order.message = order.type === 'market' ? 'اجرا روی آخرین قیمت' : 'اجرا شد';
    order.updatedAt = now;
    account.trades = account.trades.slice(-300);
  }

  async function mark(prices) {
    return store.update((account) => {
      const now = new Date().toISOString();
      for (const order of account.orders) {
        if (order.status !== 'open') continue;
        const last = prices.get(order.symbolId);
        if (!last || !crosses(order, last)) continue;
        fill(account, order, last, now);
      }
      return present(account, prices);
    });
  }

  async function place(input, quote) {
    const side = input.side === 'sell' ? 'sell' : input.side === 'buy' ? 'buy' : null;
    const type = input.type === 'limit' ? 'limit' : input.type === 'market' ? 'market' : null;
    const qty = Number(input.qty);
    if (!side || !type) throw fail('نوع سفارش نامعتبر است');
    if (!Number.isInteger(qty) || qty <= 0) throw fail('حجم باید عدد صحیح و بزرگ‌تر از صفر باشد');
    if (!quote?.last) throw fail('قیمت نماد در دسترس نیست');

    const tick = tickSize(quote.last);
    let price = type === 'market' ? quote.last : Number(input.price);
    if (type === 'limit') {
      if (!Number.isFinite(price) || price <= 0) throw fail('قیمت محدود را وارد کنید');
      price = Math.round(price);
      if (price % tick !== 0) throw fail(`قیمت باید مضرب ${tick.toLocaleString('fa-IR')} ریال باشد`);
    }

    return store.update((account) => {
      const now = new Date().toISOString();
      const order = {
        id: id('ord'),
        symbolId: quote.id,
        symbol: quote.symbol,
        name: quote.name,
        side,
        type,
        qty,
        price,
        status: 'open',
        createdAt: now,
        updatedAt: now,
        message: '',
        fillPrice: null,
      };

      if (side === 'buy' && type === 'limit') {
        const reserved = buyCost(qty, price).total;
        const reservedOpen = account.orders
          .filter((o) => o.status === 'open' && o.side === 'buy' && o.type === 'limit')
          .reduce((sum, o) => sum + buyCost(o.qty, o.price).total, 0);
        if (reserved + reservedOpen > account.cash) {
          throw fail('نقد آزاد برای این سفارش محدود کافی نیست');
        }
      }
      if (side === 'sell') {
        const pos = account.positions[quote.id];
        const openSell = account.orders
          .filter((o) => o.status === 'open' && o.side === 'sell' && o.symbolId === quote.id)
          .reduce((sum, o) => sum + o.qty, 0);
        if (!pos || pos.qty - openSell < qty) throw fail('تعداد سهم آزاد برای فروش کافی نیست');
      }
      if (side === 'buy' && type === 'market' && buyCost(qty, quote.last).total > account.cash) {
        throw fail('موجودی نقد برای خرید کافی نیست');
      }

      account.orders.push(order);
      if (crosses(order, quote.last)) fill(account, order, quote.last, now);
      const prices = new Map([[quote.id, quote.last]]);
      return present(account, prices);
    });
  }

  async function cancel(orderId, prices = new Map()) {
    return store.update((account) => {
      const order = account.orders.find((o) => o.id === orderId);
      if (!order) throw fail('سفارش پیدا نشد');
      if (order.status !== 'open') throw fail('فقط سفارش باز را می‌توان لغو کرد');
      order.status = 'cancelled';
      order.message = 'لغو شد';
      order.updatedAt = new Date().toISOString();
      return present(account, prices);
    });
  }

  async function reset() {
    return store.update((account) => {
      const fresh = emptyAccount();
      account.version = fresh.version;
      account.startingCash = fresh.startingCash;
      account.cash = fresh.cash;
      account.positions = {};
      account.orders = [];
      account.trades = [];
      return present(account, new Map());
    });
  }

  return { view, mark, place, cancel, reset };
}
