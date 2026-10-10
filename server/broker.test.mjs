import assert from 'node:assert/strict';
import test from 'node:test';
import { createBroker, emptyAccount } from './broker.mjs';
import { buyCost, sellProceeds, tickSize } from './fees.mjs';
import { marketSession } from './session.mjs';
import { symbolsFromMap } from './market.mjs';

function memoryStore(initial = emptyAccount()) {
  let account = structuredClone(initial);
  return {
    async read() {
      return account;
    },
    async update(mutator) {
      const result = await mutator(account);
      return result;
    },
  };
}

const foolad = {
  id: '453',
  symbol: 'فولاد',
  name: 'فولاد مبارکه اصفهان',
  last: 4100,
};

test('tick size follows the price bands', () => {
  assert.equal(tickSize(750), 1);
  assert.equal(tickSize(4100), 10);
  assert.equal(tickSize(13520), 50);
  assert.equal(tickSize(49560), 100);
  assert.equal(tickSize(315000), 1000);
});

test('market buy debits cash including fee and opens a position', async () => {
  const broker = createBroker(memoryStore());
  const view = await broker.place({ side: 'buy', type: 'market', qty: 1000 }, foolad);
  const cost = buyCost(1000, 4100);
  const position = view.positions[0];
  assert.equal(view.cash, 5_000_000_000 - cost.total);
  assert.equal(position.qty, 1000);
  assert.equal(position.cost, cost.total);
  assert.equal(view.trades[0].side, 'buy');
  assert.equal(view.orders[0].status, 'filled');
});

test('buy is rejected when cash is short', async () => {
  const broker = createBroker(memoryStore());
  await assert.rejects(
    broker.place({ side: 'buy', type: 'market', qty: 2_000_000 }, foolad),
    /کافی نیست/,
  );
});

test('limit buy below the last price rests and can be cancelled', async () => {
  const broker = createBroker(memoryStore());
  let view = await broker.place({ side: 'buy', type: 'limit', qty: 100, price: 4000 }, foolad);
  assert.equal(view.orders[0].status, 'open');
  assert.equal(view.cash, 5_000_000_000);
  view = await broker.cancel(view.orders[0].id);
  assert.equal(view.orders[0].status, 'cancelled');
});

test('limit buy at or above the last price fills at the last price', async () => {
  const broker = createBroker(memoryStore());
  const view = await broker.place({ side: 'buy', type: 'limit', qty: 10, price: 4200 }, foolad);
  assert.equal(view.orders[0].status, 'filled');
  assert.equal(view.orders[0].fillPrice, 4100);
  assert.equal(view.trades[0].price, 4100);
});

test('a resting limit fills when the board price crosses it', async () => {
  const broker = createBroker(memoryStore());
  await broker.place({ side: 'buy', type: 'limit', qty: 50, price: 4000 }, foolad);
  const view = await broker.mark(new Map([['453', 3990]]));
  assert.equal(view.orders[0].status, 'filled');
  assert.equal(view.orders[0].fillPrice, 3990);
  assert.equal(view.positions[0].qty, 50);
});

test('sell realizes proceeds after the higher sell fee', async () => {
  const broker = createBroker(memoryStore());
  await broker.place({ side: 'buy', type: 'market', qty: 200 }, foolad);
  const view = await broker.place({ side: 'sell', type: 'market', qty: 80 }, { ...foolad, last: 4300 });
  const proceeds = sellProceeds(80, 4300);
  assert.equal(view.positions[0].qty, 120);
  assert.equal(view.trades[0].fee, proceeds.fee);
  assert.equal(view.positions.length, 1);
});

test('selling more than the free quantity is rejected', async () => {
  const broker = createBroker(memoryStore());
  await broker.place({ side: 'buy', type: 'market', qty: 10 }, foolad);
  await assert.rejects(
    broker.place({ side: 'sell', type: 'market', qty: 11 }, foolad),
    /کافی نیست/,
  );
});

test('two buys keep a fee-inclusive average cost', async () => {
  const broker = createBroker(memoryStore());
  await broker.place({ side: 'buy', type: 'market', qty: 100 }, foolad);
  const view = await broker.place({ side: 'buy', type: 'market', qty: 50 }, { ...foolad, last: 4200 });
  const expected = buyCost(100, 4100).total + buyCost(50, 4200).total;
  assert.equal(view.positions[0].qty, 150);
  assert.equal(view.positions[0].cost, expected);
});

test('saturday morning in Tehran is an open session', () => {
  const session = marketSession(new Date('2026-10-10T06:30:00Z'));
  assert.equal(session.open, true);
  assert.equal(session.label, 'باز');
});

test('friday is a holiday and afternoon is closed', () => {
  assert.equal(marketSession(new Date('2026-10-09T07:00:00Z')).label, 'تعطیل');
  assert.equal(marketSession(new Date('2026-10-10T11:30:00Z')).label, 'بسته');
  assert.equal(marketSession(new Date('2026-10-10T05:20:00Z')).label, 'پیش‌گشایش');
});

test('market map leaves become symbols grouped by industry', () => {
  const symbols = symbolsFromMap({
    data: [
      {
        root: {
          id: 'root',
          name: 'نقشه بازار',
          children: [
            {
              id: '47',
              name: 'فلزات',
              fullname: 'فلزات اساسی',
              children: [
                { id: '453', name: 'فولاد', fullname: 'فولاد مبارکه', real_close_price: 4100, value: 0.02, area: 100 },
              ],
            },
            { id: '9', name: 'تک', fullname: 'نماد تک', real_close_price: 1000, value: -0.01, area: 5 },
          ],
        },
      },
    ],
  });
  assert.equal(symbols.length, 2);
  const foolad = symbols.find((symbol) => symbol.symbol === 'فولاد');
  const single = symbols.find((symbol) => symbol.symbol === 'تک');
  assert.equal(foolad?.sector, 'فلزات اساسی');
  assert.equal(foolad?.changePercent, 2);
  assert.equal(single?.sector, 'بازار');
});
