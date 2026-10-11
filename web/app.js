const listsEl = document.querySelector("#lists");
const statusEl = document.querySelector("#status");
const disclaimerEl = document.querySelector("#disclaimer");
const sourceNoteEl = document.querySelector("#source-note");
const indicesEl = document.querySelector("#indices");
const drawer = document.querySelector("#drawer");
const drawerBody = document.querySelector("#drawer-body");
const query = document.querySelector("#query");

const ORDER = [
  "buy_now",
  "buy_in_red",
  "pre_queue",
  "sell_now",
  "distribution",
  "locked_buy",
  "locked_sell",
  "halted",
];

const INDICATORS = [
  ["rsi", "RSI"],
  ["macd_hist", "هیستوگرام مکدی"],
  ["macd_cross", "تقاطع مکدی"],
  ["stoch_k", "استوکاستیک K"],
  ["stoch_d", "استوکاستیک D"],
  ["bb_pct_b", "بولینگر٪"],
  ["sma20", "میانگین ۲۰"],
  ["sma50", "میانگین ۵۰"],
  ["ema9", "نمایی ۹"],
  ["ema21", "نمایی ۲۱"],
  ["adx", "ADX"],
  ["plus_di", "+DI"],
  ["minus_di", "−DI"],
  ["atr_pct", "ATR٪"],
  ["cci", "CCI"],
  ["mfi", "MFI"],
  ["williams_r", "ویلیامز٪R"],
  ["obv_slope", "شیب OBV"],
  ["roc3", "بازده ۳روزه"],
  ["roc5", "بازده ۵روزه"],
  ["roc7", "بازده ۷روزه"],
  ["volume_ratio", "حجم به میانگین"],
  ["ichimoku", "ایچیموکو"],
];

let board = null;

const fa = (value, digits = 0) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
};

const signed = (value, digits = 1) => {
  if (value === null || value === undefined) return "—";
  const text = fa(Math.abs(value), digits);
  if (value > 0) return `+${text}`;
  if (value < 0) return `−${text}`;
  return text;
};

const compact = (value) => {
  if (value === null || value === undefined) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (abs >= 1e9) return `${sign}${fa(abs / 1e9, 1)} میلیارد`;
  if (abs >= 1e6) return `${sign}${fa(abs / 1e6, 1)} میلیون`;
  return `${sign}${fa(abs, 0)}`;
};

const cls = (value) => (value > 0 ? "up" : value < 0 ? "down" : "");
const ltr = (text) => `<bdi dir="ltr">${text}</bdi>`;

function renderStatus() {
  const market = board.market || {};
  const source = board.source || {};
  const phaseClass = market.phase === "open" ? "open" : "closed";
  statusEl.innerHTML = `
    <span class="pill ${phaseClass}">${market.phase_label || "نامشخص"}</span>
    <span class="pill">${ltr(market.clock || "")} تهران</span>
    <span class="pill ${source.live ? "" : "sample"}">${source.live ? "دادهٔ زنده" : "نمونهٔ آموزشی"}</span>
    <span class="pill">${fa(board.scanned || 0)} نماد</span>
  `;
  disclaimerEl.textContent = board.disclaimer || "";
  if (source.note && !source.live) {
    sourceNoteEl.hidden = false;
    sourceNoteEl.textContent = source.note;
  } else {
    sourceNoteEl.hidden = true;
  }
  indicesEl.innerHTML = (board.indices || []).map((item) => `
    <div class="index">
      <span>${item.name}</span>
      <b>${ltr(fa(item.value, 0))}</b>
      <span class="${cls(item.change_percent)}">${ltr(`${signed(item.change_percent, 2)}٪`)}</span>
    </div>
  `).join("");
}

function cardHtml(card) {
  const scores = card.scores || {};
  const bits = [
    ["تکنیکال", scores.technical],
    ["بنیادی", scores.fundamental],
    ["تابلو", scores.tape],
    ["بازیگر", scores.players],
  ];
  return `
    <button class="card" type="button" data-symbol="${card.symbol}" data-bucket="${card.bucket}">
      <div class="card-top">
        <div>
          <div class="symbol">${card.symbol}</div>
          <div class="name">${card.name || ""}</div>
        </div>
        <div class="pct ${cls(card.pct_last)}">${ltr(`${signed(card.pct_last, 2)}٪`)}</div>
      </div>
      <div class="meta">
        <span>آخرین ${ltr(fa(card.last, 0))}</span>
        <span>پایانی ${ltr(`${signed(card.pct_close, 2)}٪`)}</span>
      </div>
      <p class="thesis">${card.thesis || ""}</p>
      <div class="tags">${(card.tags || []).map((tag) => `<span class="tag">${tag}</span>`).join("")}</div>
      <div class="scores">
        ${bits.map(([label, value]) => `<span>${label} ${fa(value, 0)}</span>`).join("")}
        <span>کمیته ${fa(card.consensus, 0)}</span>
      </div>
    </button>
  `;
}

function renderLists() {
  const needle = query.value.trim();
  const copy = board.list_copy || {};
  listsEl.innerHTML = ORDER.map((key) => {
    const rows = (board.lists?.[key] || []).filter((card) => !needle || `${card.symbol} ${card.name}`.includes(needle));
    const meta = copy[key] || { title: key, blurb: "" };
    const body = rows.length
      ? `<div class="cards">${rows.map(cardHtml).join("")}</div>`
      : `<p class="empty">در این فهرست نمادی نیست.</p>`;
    return `
      <section class="list" id="list-${key}">
        <header>
          <h2>${meta.title}</h2>
          <span>${fa(rows.length)} سهم</span>
        </header>
        <p class="blurb">${meta.blurb || ""}</p>
        ${body}
      </section>
    `;
  }).join("");
}

function findCard(symbol, bucket) {
  return (board.lists?.[bucket] || []).find((card) => card.symbol === symbol);
}

function openCard(card) {
  const flow = card.flow || {};
  const fund = card.fundamentals || {};
  const ind = card.indicators || {};
  const teams = Object.values(card.teams || {});
  drawer.hidden = false;
  drawerBody.innerHTML = `
    <div class="card-top">
      <div>
        <div class="symbol">${card.symbol}</div>
        <div class="name">${card.name} · ${card.industry || ""}</div>
      </div>
      <div class="pct ${cls(card.pct_last)}">${ltr(`${signed(card.pct_last, 2)}٪`)}</div>
    </div>
    <p>${card.execution_note || ""}</p>
    <section class="drawer-panel">
      <h3>تابلو و سرانه</h3>
      <div class="ind-grid">
        <div><span>قدرت خریدار حقیقی</span><b>${fa(flow.buyer_power, 2)}</b></div>
        <div><span>سرانه خرید</span><b>${fa(flow.buy_per_capita_mt, 1)} م.تومان</b></div>
        <div><span>سرانه فروش</span><b>${fa(flow.sell_per_capita_mt, 1)} م.تومان</b></div>
        <div><span>حجم به مبنا</span><b>${fa(flow.volume_to_base, 2)}</b></div>
        <div><span>خالص حقوقی امروز</span><b>${compact(flow.legal_net_today)}</b></div>
        <div><span>خالص حقوقی ۳روز</span><b>${compact(flow.net_legal_3)}</b></div>
        <div><span>خالص حقوقی ۵روز</span><b>${compact(flow.net_legal_5)}</b></div>
        <div><span>خالص حقوقی ۷روز</span><b>${compact(flow.net_legal_7)}</b></div>
        <div><span>روزهای پیاپی خرید حقوقی</span><b>${fa(flow.legal_buy_streak, 0)}</b></div>
        <div><span>جایگاه در دامنه</span><b>${fa(card.range_position, 0)}٪</b></div>
      </div>
    </section>
    <section class="drawer-panel">
      <h3>بنیادی لحظه‌ای</h3>
      <div class="ind-grid">
        <div><span>P/E</span><b>${fa(fund.pe, 2)}</b></div>
        <div><span>P/E گروه</span><b>${fa(fund.group_pe, 2)}</b></div>
        <div><span>P/S</span><b>${fa(fund.ps, 2)}</b></div>
        <div><span>P/B</span><b>${fa(fund.pb, 2)}</b></div>
        <div><span>EPS</span><b>${fa(fund.eps, 1)}</b></div>
        <div><span>شناوری</span><b>${fa(fund.float_percent, 0)}٪</b></div>
      </div>
    </section>
    <section class="drawer-panel">
      <h3>تکنیکال</h3>
      <div class="ind-grid">
        ${INDICATORS.map(([key, label]) => `<div><span>${label}</span><b>${formatInd(ind[key])}</b></div>`).join("")}
      </div>
    </section>
    ${teams.map((team) => `
      <section class="drawer-panel team">
        <h3>${team.title} <span class="stance">${fa(team.score, 0)} · ${stanceLabel(team.stance)}</span></h3>
        <ul>${(team.reasons || []).map((reason) => `<li>${reason}</li>`).join("")}</ul>
      </section>
    `).join("")}
  `;
}

function formatInd(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return fa(value, 2);
  if (value === "above") return "بالای ابر";
  if (value === "below") return "زیر ابر";
  if (value === "inside") return "داخل ابر";
  if (value === "up") return "تقاطع صعودی";
  if (value === "down") return "تقاطع نزولی";
  if (value === "none") return "بدون تقاطع تازه";
  return String(value);
}

function stanceLabel(stance) {
  return { buy: "موافق خرید", sell: "موافق فروش", watch: "خنثی", avoid: "پرهیز", unknown: "داده ناقص" }[stance] || stance || "";
}

async function load(force = false) {
  const response = await fetch(`/api/board${force ? "?force=true" : ""}`);
  board = await response.json();
  renderStatus();
  renderLists();
  const open = new URLSearchParams(location.search).get("open");
  if (open) {
    for (const key of ORDER) {
      const card = (board.lists?.[key] || []).find((item) => item.symbol === open);
      if (card) {
        openCard(card);
        break;
      }
    }
  }
}

listsEl.addEventListener("click", (event) => {
  const button = event.target.closest(".card");
  if (!button || !board) return;
  const card = findCard(button.dataset.symbol, button.dataset.bucket);
  if (card) openCard(card);
});
document.querySelector("#close-drawer").addEventListener("click", () => {
  drawer.hidden = true;
});
document.querySelector("#refresh").addEventListener("click", () => load(true));
query.addEventListener("input", () => board && renderLists());

load();
setInterval(() => load(false), 15000);
