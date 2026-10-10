import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createBroker } from './broker.mjs';
import { createMarket } from './market.mjs';
import { marketSession } from './session.mjs';
import { createStore } from './store.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.join(ROOT, '..', 'dist');
const PORT = Number(process.env.PORT || 8787);
const store = createStore(path.join(ROOT, '..', 'data', 'account.json'));
const broker = createBroker(store);
const market = createMarket();

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.woff2': 'font/woff2',
};

function send(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  });
  res.end(payload);
}

async function accountView() {
  const board = await market.board();
  let account;
  try {
    account = await broker.mark(market.prices());
  } catch {
    account = await broker.view(market.prices());
  }
  return { board, account };
}

async function handleApi(req, res, url) {
  try {
    if (req.method === 'GET' && url.pathname === '/api/health') {
      send(res, 200, { ok: true });
      return;
    }
    if (req.method === 'GET' && url.pathname === '/api/overview') {
      const { board, account } = await accountView();
      send(res, 200, { ...board, session: marketSession(), account });
      return;
    }
    if (req.method === 'GET' && url.pathname === '/api/search') {
      await market.board();
      send(res, 200, { symbols: await market.search(url.searchParams.get('q') || '') });
      return;
    }
    const quoteMatch = url.pathname.match(/^\/api\/symbols\/([^/]+)$/);
    if (req.method === 'GET' && quoteMatch) {
      await market.board();
      const quote = await market.quote(decodeURIComponent(quoteMatch[1]));
      const account = await broker.mark(market.prices());
      send(res, 200, { quote, account });
      return;
    }
    const candleMatch = url.pathname.match(/^\/api\/symbols\/([^/]+)\/candles$/);
    if (req.method === 'GET' && candleMatch) {
      const candles = await market.candles(decodeURIComponent(candleMatch[1]));
      send(res, 200, { candles });
      return;
    }
    if (req.method === 'GET' && url.pathname === '/api/account') {
      await market.board();
      send(res, 200, await broker.mark(market.prices()));
      return;
    }
    if (req.method === 'POST' && url.pathname === '/api/orders') {
      const input = await readBody(req);
      await market.board();
      const quote = await market.quote(String(input.symbolId || ''));
      const account = await broker.place(input, quote);
      send(res, 200, account);
      return;
    }
    const cancelMatch = url.pathname.match(/^\/api\/orders\/([^/]+)$/);
    if (req.method === 'DELETE' && cancelMatch) {
      await market.board();
      const account = await broker.cancel(decodeURIComponent(cancelMatch[1]), market.prices());
      send(res, 200, account);
      return;
    }
    if (req.method === 'POST' && url.pathname === '/api/account/reset') {
      await broker.reset();
      await market.board();
      send(res, 200, await broker.view(market.prices()));
      return;
    }
    send(res, 404, { error: 'مسیر پیدا نشد' });
  } catch (error) {
    const status = error?.status || 500;
    send(res, status, { error: error instanceof Error ? error.message : 'خطای سرور' });
  }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => {
      if (!chunks.length) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
      } catch {
        reject(Object.assign(new Error('بدنه درخواست نامعتبر است'), { status: 400 }));
      }
    });
    req.on('error', reject);
  });
}

async function serveStatic(req, res, url) {
  const requested = url.pathname === '/' ? '/index.html' : url.pathname;
  const filePath = path.normalize(path.join(DIST, requested));
  if (!filePath.startsWith(DIST)) {
    send(res, 403, { error: 'forbidden' });
    return;
  }
  const indexPath = path.join(DIST, 'index.html');
  try {
    await stat(indexPath);
  } catch {
    send(res, 503, { error: 'رابط کاربری هنوز ساخته نشده است. دستور npm run dev را اجرا کنید.' });
    return;
  }
  try {
    const info = await stat(filePath);
    if (!info.isFile()) throw new Error('not file');
    res.writeHead(200, {
      'Content-Type': TYPES[path.extname(filePath)] || 'application/octet-stream',
    });
    createReadStream(filePath).pipe(res);
  } catch {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    createReadStream(indexPath).pipe(res);
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
  if (url.pathname.startsWith('/api/')) {
    await handleApi(req, res, url);
    return;
  }
  await serveStatic(req, res, url);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`talar listening on ${PORT}`);
});
