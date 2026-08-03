"use client";

import { useMemo, useState } from "react";

type Allocation = { ticker: string; weight: number; name: string; role: string };

const money = (value: number) =>
  new Intl.NumberFormat("zh-HK", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const pct = (value: number) =>
  new Intl.NumberFormat("zh-HK", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value);

export default function AllocationCalculator({ allocations }: { allocations: Allocation[] }) {
  const [capital, setCapital] = useState(1_000);
  const safeCapital = useMemo(() => Math.max(0, Math.min(capital || 0, 100_000_000)), [capital]);

  return (
    <div className="calculator-shell">
      <div className="capital-control">
        <label htmlFor="capital">我的試算資金（美元）</label>
        <div className="money-input"><span>$</span><input id="capital" inputMode="decimal" type="number" min="0" max="100000000" step="100" value={capital} onChange={(event) => setCapital(Number(event.target.value))} /></div>
        <div className="quick-values" aria-label="快速選擇資金">
          {[1_000, 5_000, 10_000, 50_000].map((amount) => <button type="button" className={capital === amount ? "active" : ""} onClick={() => setCapital(amount)} key={amount}>{money(amount)}</button>)}
        </div>
        <p>僅依目標權重換算；未計股數、零股限制、匯率和實際成交價。</p>
      </div>
      <div className="allocation-list">
        {allocations.map((item) => (
          <article key={item.ticker}>
            <div className="ticker"><b>{item.ticker}</b><span>{item.role}</span></div>
            <div className="asset"><b>{item.name}</b><span>{pct(item.weight)}</span></div>
            <strong>{money(safeCapital * item.weight)}</strong>
            <div className="weight-bar"><i style={{ width: `${item.weight * 100}%` }} /></div>
          </article>
        ))}
      </div>
    </div>
  );
}
