import type { Unit } from './types';

const PERSIAN = '۰۱۲۳۴۵۶۷۸۹';
const ARABIC = '٠١٢٣٤٥٦٧٨٩';

export function parseNumber(raw: string): number {
  let text = raw.trim();
  for (let i = 0; i < 10; i += 1) {
    text = text.replaceAll(PERSIAN[i], String(i)).replaceAll(ARABIC[i], String(i));
  }
  text = text.replace(/[٬,\s]/g, '');
  const value = Number(text);
  return Number.isFinite(value) ? value : Number.NaN;
}

export function formatNumber(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('fa-IR', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function toUnit(rial: number, unit: Unit): number {
  return unit === 'toman' ? rial / 10 : rial;
}

export function formatMoney(rial: number, unit: Unit, digits?: number): string {
  const value = toUnit(rial, unit);
  const fraction = digits ?? (unit === 'toman' && Math.abs(value % 1) > 0.001 ? 1 : 0);
  return formatNumber(value, fraction);
}

export function unitLabel(unit: Unit): string {
  return unit === 'toman' ? 'تومان' : 'ریال';
}

export function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatNumber(value, 2)}٪`;
}

export function formatCompact(value: number, unit: Unit): string {
  const scaled = Math.abs(toUnit(value, unit));
  const sign = value < 0 ? '-' : '';
  if (scaled >= 1e12) return `${sign}${formatNumber(scaled / 1e12, 2)} هزار میلیارد`;
  if (scaled >= 1e9) return `${sign}${formatNumber(scaled / 1e9, 2)} میلیارد`;
  if (scaled >= 1e6) return `${sign}${formatNumber(scaled / 1e6, 2)} میلیون`;
  if (scaled >= 1e3) return `${sign}${formatNumber(scaled / 1e3, 1)} هزار`;
  return formatMoney(value, unit);
}

export function formatClock(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('fa-IR', {
    timeZone: 'Asia/Tehran',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function tone(value: number | null | undefined): 'up' | 'down' | 'flat' {
  if (value == null || !Number.isFinite(value) || value === 0) return 'flat';
  return value > 0 ? 'up' : 'down';
}

export function heatColor(percent: number): string {
  const t = Math.max(-3, Math.min(3, percent)) / 3;
  const mix = (from: number[], to: number[], amount: number) =>
    from.map((channel, index) => Math.round(channel + (to[index] - channel) * amount));
  const mid = [32, 48, 64];
  const pos = [18, 122, 78];
  const neg = [148, 42, 52];
  const [r, g, b] = t >= 0 ? mix(mid, pos, t) : mix(mid, neg, -t);
  return `rgb(${r}, ${g}, ${b})`;
}
