"use client";

import { Children, useEffect, useId, useState, type KeyboardEvent, type ReactNode } from "react";

type StrategyKey = "stable" | "aggressive";

const tabs: Array<{
  key: StrategyKey;
  eyebrow: string;
  label: string;
  detail: string;
  status: string;
}> = [
  {
    key: "stable",
    eyebrow: "LONG TERM",
    label: "長線穩定",
    detail: "ETF 分散 · 控制最大跌幅",
    status: "Paper-only",
  },
  {
    key: "aggressive",
    eyebrow: "SHORT TERM",
    label: "短線高回報",
    detail: "大型股動量 · 先驗證後 Paper",
    status: "研究中",
  },
];

export default function StrategyTabs({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<StrategyKey>("stable");
  const id = useId();
  const panels = Children.toArray(children);

  useEffect(() => {
    const syncHash = () => {
      if (window.location.hash === "#short-term") {
        setActive("aggressive");
      } else if (window.location.hash === "#long-term") {
        setActive("stable");
      }
    };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  const select = (next: StrategyKey) => {
    setActive(next);
    window.history.replaceState(null, "", `#${next === "stable" ? "long-term" : "short-term"}`);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!(["ArrowLeft", "ArrowRight", "Home", "End"] as string[]).includes(event.key)) {
      return;
    }
    event.preventDefault();
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? tabs.length - 1
        : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    const next = tabs[nextIndex];
    select(next.key);
    document.getElementById(`${id}-${next.key}-tab`)?.focus();
  };

  return (
    <div className="strategy-tabs-shell" data-active-strategy={active}>
      <section className="strategy-switch" id="strategy-tabs" aria-label="策略選擇">
        <div className="wrap strategy-switch-inner">
          <div className="strategy-switch-intro">
            <span>SELECT A RESEARCH TRACK</span>
            <b>兩條策略，兩套目標與門檻</b>
          </div>
          <div className="strategy-tablist" role="tablist" aria-label="選擇研究策略">
            {tabs.map((tab, index) => {
              const selected = active === tab.key;
              return (
                <button
                  type="button"
                  role="tab"
                  id={`${id}-${tab.key}-tab`}
                  aria-selected={selected}
                  aria-controls={`${id}-${tab.key}-panel`}
                  tabIndex={selected ? 0 : -1}
                  className={selected ? "active" : ""}
                  onClick={() => select(tab.key)}
                  onKeyDown={(event) => onKeyDown(event, index)}
                  key={tab.key}
                >
                  <span>{tab.eyebrow}</span>
                  <strong>{tab.label}</strong>
                  <small>{tab.detail}</small>
                  <i>{tab.status}</i>
                </button>
              );
            })}
          </div>
        </div>
      </section>
      <div
        role="tabpanel"
        id={`${id}-stable-panel`}
        aria-labelledby={`${id}-stable-tab`}
        hidden={active !== "stable"}
      >
        {panels[0]}
      </div>
      <div
        role="tabpanel"
        id={`${id}-aggressive-panel`}
        aria-labelledby={`${id}-aggressive-tab`}
        hidden={active !== "aggressive"}
      >
        {panels[1]}
      </div>
    </div>
  );
}
