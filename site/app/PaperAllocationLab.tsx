"use client";

import { useMemo, useState } from "react";

const money = (value: number) =>
  new Intl.NumberFormat("zh-HK", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const allocations = [
  { ticker: "VUG", name: "美國大型成長股", role: "成長核心", weight: 0.8 },
  { ticker: "GLD", name: "實物黃金", role: "分散袖套", weight: 0.2 },
];

export default function PaperAllocationLab({ paperOnly }: { paperOnly: boolean }) {
  const [capital, setCapital] = useState(1_000);
  const safeCapital = useMemo(
    () => Math.max(0, Math.min(capital || 0, 100_000_000)),
    [capital],
  );

  if (paperOnly) {
    return (
      <div className="paper-allocation-lab allocation-locked" data-allocation-visible="false">
        <div className="paper-lab-heading">
          <div>
            <span>REAL-MONEY LOCK · 只供 PAPER 驗證</span>
            <h3>今天不下單</h3>
          </div>
          <p>
            實金 readiness 未達 11/11；配置百分比、金額換算及快速本金按鈕暫不顯示。
          </p>
        </div>
        <div className="allocation-lock-notice" role="status">
          <strong>實金動作 US$0</strong>
          <p>Paper 持倉及歷史最後權重不是交易建議；待全部前瞻門檻通過後才重新評估顯示。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="paper-allocation-lab">
      <div className="paper-lab-heading">
        <div>
          <span>前瞻門檻通過 · 參考試算</span>
          <h3>以 US$1,000 看懂固定 80/20</h3>
        </div>
        <p>只換算目標權重；實際股數、稅務、匯率與成交價格仍需自行核對。</p>
      </div>
      <div className="calculator-shell paper-calculator">
        <div className="capital-control">
          <label htmlFor="v25-paper-capital">參考本金（美元）</label>
          <div className="money-input">
            <span>$</span>
            <input
              id="v25-paper-capital"
              inputMode="decimal"
              type="number"
              min="0"
              max="100000000"
              step="100"
              value={capital}
              onChange={(event) => setCapital(Number(event.target.value))}
            />
          </div>
          <div className="quick-values" aria-label="快速選擇 Paper 本金">
            {[1_000, 5_000, 10_000, 50_000].map((amount) => (
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
            此處只是配置參考，不會自動落盤或保證成交；未計碎股限制、佣金、買賣差價、匯率及稅項。
          </p>
        </div>
      </div>
    </div>
  );
}
