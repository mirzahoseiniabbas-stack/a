import type { Account, Candle, Overview, Quote, SymbolRow } from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  const data = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) throw new Error(data.error || 'خطا در ارتباط با سرور');
  return data;
}

export const api = {
  overview: () => request<Overview>('/api/overview'),
  search: (q: string) => request<{ symbols: SymbolRow[] }>(`/api/search?q=${encodeURIComponent(q)}`),
  quote: (id: string) => request<{ quote: Quote; account: Account }>(`/api/symbols/${encodeURIComponent(id)}`),
  candles: (id: string) => request<{ candles: Candle[] }>(`/api/symbols/${encodeURIComponent(id)}/candles`),
  order: (body: { symbolId: string; side: 'buy' | 'sell'; type: 'market' | 'limit'; qty: number; price?: number }) =>
    request<Account>('/api/orders', { method: 'POST', body: JSON.stringify(body) }),
  cancel: (id: string) => request<Account>(`/api/orders/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  reset: () => request<Account>('/api/account/reset', { method: 'POST', body: '{}' }),
};
