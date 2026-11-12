export function formatINR(
  val: number | null | undefined,
  mode: 'compact' | 'full' = 'compact'
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  const isNeg = val < 0;
  const abs = Math.abs(val);

  if (mode === 'compact') {
    if (abs >= 1e7) {
      const cr = abs / 1e7;
      return `${isNeg ? '-' : ''}₹${cr.toFixed(2)} Cr`;
    }
    if (abs >= 1e5) {
      const lk = abs / 1e5;
      return `${isNeg ? '-' : ''}₹${lk.toFixed(2)} L`;
    }
  }

  const rounded = Math.round(abs);
  const formatted = rounded.toLocaleString('en-IN');
  return `${isNeg ? '-' : ''}₹${formatted}`;
}

export function formatMW(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  return `${val.toLocaleString('en-IN', { maximumFractionDigits: 1 })} MW`;
}

export function formatMWh(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  return `${val.toLocaleString('en-IN', { maximumFractionDigits: 0 })} MWh`;
}

export function formatPct(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) {
    return '—';
  }
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}
