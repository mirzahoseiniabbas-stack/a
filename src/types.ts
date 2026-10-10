export type Unit = 'rial' | 'toman';

export interface SymbolRow {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  last: number;
  change: number;
  changePercent: number;
  value: number;
}

export interface IndexRow {
  id: string;
  name: string;
  value: number;
  change: number;
  changePercent: number;
  asOf?: string | null;
}

export interface SessionInfo {
  open: boolean;
  phase: string;
  label: string;
  clock: string;
  note: string;
}

export interface Quote {
  id: string;
  symbol: string;
  name: string;
  english: string;
  sector: string;
  exchange: string;
  state: string | null;
  last: number;
  close: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  prev: number;
  volume: number;
  value: number;
  trades: number;
  buyers: number;
  buyPower: number | null;
  realBuyVolume: number;
  realSellVolume: number;
  legalBuyVolume: number;
  legalSellVolume: number;
  tick: number;
  asOf: string | null;
  source: string;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Position {
  symbolId: string;
  symbol: string;
  name: string;
  qty: number;
  avgCost: number;
  cost: number;
  last: number | null;
  marketValue: number | null;
  pnl: number | null;
  pnlPercent: number;
  exitPnl: number | null;
}

export interface Order {
  id: string;
  symbolId: string;
  symbol: string;
  name: string;
  side: 'buy' | 'sell';
  type: 'market' | 'limit';
  qty: number;
  price: number;
  status: 'open' | 'filled' | 'cancelled' | 'rejected';
  createdAt: string;
  updatedAt: string;
  message: string;
  fillPrice: number | null;
}

export interface Trade {
  id: string;
  orderId: string;
  symbolId: string;
  symbol: string;
  name: string;
  side: 'buy' | 'sell';
  qty: number;
  price: number;
  fee: number;
  gross: number;
  time: string;
}

export interface Account {
  cash: number;
  startingCash: number;
  positions: Position[];
  orders: Order[];
  trades: Trade[];
  stockValue: number;
  equity: number;
  pnl: number;
}

export interface Overview {
  source: 'live' | 'snapshot';
  asOf: string | null;
  note: string;
  error: string | null;
  indices: IndexRow[];
  symbols: SymbolRow[];
  session: SessionInfo;
  account: Account;
}
