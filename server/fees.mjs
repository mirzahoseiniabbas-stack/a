/** نرخ متعارف کارمزد معاملات سهام در بورس تهران، به اعشار. */
export const BUY_FEE_RATE = 0.003712;
export const SELL_FEE_RATE = 0.0088;

export function tickSize(price) {
  const p = Math.abs(Number(price) || 0);
  if (p <= 2000) return 1;
  if (p <= 10000) return 10;
  if (p <= 20000) return 50;
  if (p <= 50000) return 100;
  if (p <= 100000) return 500;
  return 1000;
}

export function buyCost(qty, price) {
  const gross = Math.round(qty * price);
  const fee = Math.round(gross * BUY_FEE_RATE);
  return { gross, fee, total: gross + fee };
}

export function sellProceeds(qty, price) {
  const gross = Math.round(qty * price);
  const fee = Math.round(gross * SELL_FEE_RATE);
  return { gross, fee, total: gross - fee };
}

/** قیمت فروش لازم برای جبران بهای تمام‌شده هر سهم، با کارمزد فروش. */
export function breakEven(avgCost) {
  if (!avgCost) return 0;
  return avgCost / (1 - SELL_FEE_RATE);
}
