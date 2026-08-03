"use client";

import { useMemo, useState } from "react";

const money = (value: number) =>
  new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const allocations = [
  { ticker: "VUG", name: "美國大型成長股", role: "成長核心", weight: 0.8 },
  { ticker: "GLD", name: "實物黃金", role: "分散袖套", weight: 0.2 },
];

export default function PaperAllocationLab({ paperOnly }: { paperOnly: boolean }) {
  const [capital, setCapital] = useState(100_000);
  const safeCapital = useMemo(
    () => Math.max(0, Math.min(capital || 0, 100_000_000)),
    [capital],
  );

  return (
    <div className="paper-allocation-lab">
      <div className="paper-lab-heading">
        <div>
          <span>{paperOnly ? "PAPER 模擬交易試算 · 不會落盤" : "前瞻門檻通過 · 參考試算"}</span>
          <h3>把 80/20 換成看得懂的金額</h3>
        </div>
        <p>
          {paperOnly
            ? "只用來理解固定權重怎麼運作；不連證券商、不計股數，也不代表現在應投入這筆錢。"
            : "只換算目標權重；實際股數、稅務、匯率與成交價格仍需自行核對。"}
        </p>
      </div>
      <div className="calculator-shell paper-calculator">
        <div className="capital-control">
          <label htmlFor="v25-paper-capital">
            {paperOnly ? "假設的 Paper 本金（美元）" : "參考本金（美元）"}
          </label>
          <div className="money-input">
            <span>$</span>
            <input
              id="v25-paper-capital"
              inputMode="decimal"
              type="number"
              min="0"
              max="100000000"
              step="1000"
              value={capital}
              onChange={(event) => setCapital(Number(event.target.value))}
            />
          </div>
          <div className="quick-values" aria-label="快速選擇 Paper 本金">
            {[10_000, 50_000, 100_000, 500_000].map((amount) => (
              <button
                type="button"
                className={capital === amount ? "active" : ""}
                onClick={() => setCapital(amount)}
                key={amount}
              >
                {money(amount)}
              </button>
            ))}
          </div>
          <p>規則是在每個完整月末檢查並拉回 80/20；月中漲跌不臨時改權重。</p>
        </div>
        <div className="allocation-list">
          {allocations.map((item) => (
            <article key={item.ticker}>
              <div className="ticker">
                <b>{item.ticker}</b>
                <span>{item.role}</span>
              </div>
              <div className="asset">
                <b>{item.name}</b>
                <span>{Math.round(item.weight * 100)}% 目標</span>
              </div>
              <strong>{money(safeCapital * item.weight)}</strong>
              <div className="weight-bar">
                <i style={{ width: `${item.weight * 100}%` }} />
              </div>
            </article>
          ))}
          <p className="paper-calculator-warning">
            {paperOnly
              ? "目前實金動作仍是 0；這兩個金額只存在於瀏覽器試算，不會寫入 Paper 模擬組合。"
              : "此處只是配置參考，不會自動落盤或保證成交。"}
          </p>
        </div>
      </div>
    </div>
  );
}
