export const BUY_FEE_RATE = 0.003712;
export const SELL_FEE_RATE = 0.0088;

export function BUY_PREVIEW(qty: number, price: number) {
  const gross = Math.round(qty * price);
  const fee = Math.round(gross * BUY_FEE_RATE);
  return { gross, fee, total: gross + fee };
}

export function SELL_PREVIEW(qty: number, price: number) {
  const gross = Math.round(qty * price);
  const fee = Math.round(gross * SELL_FEE_RATE);
  return { gross, fee, total: gross - fee };
}

export function maxBuyQty(cash: number, price: number): number {
  if (price <= 0) return 0;
  const unit = price * (1 + BUY_FEE_RATE);
  return Math.max(0, Math.floor(cash / unit));
}
