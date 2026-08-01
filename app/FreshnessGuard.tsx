"use client";

import { useEffect, useState } from "react";

type Freshness = "checking" | "fresh" | "stale";

export default function FreshnessGuard({
  dataThrough,
  refreshDueAtUtc,
}: {
  dataThrough: string;
  refreshDueAtUtc: string;
}) {
  const [status, setStatus] = useState<Freshness>("checking");

  useEffect(() => {
    const update = () => {
      const next = Date.now() > Date.parse(refreshDueAtUtc) ? "stale" : "fresh";
      document.documentElement.dataset.signalFreshness = next;
      setStatus(next);
    };
    update();
    const timer = window.setInterval(update, 60_000);
    return () => window.clearInterval(timer);
  }, [refreshDueAtUtc]);

  if (status === "stale") {
    return <span className="data-date stale-date">訊號已停用 · 資料只到 {dataThrough}</span>;
  }
  if (status === "fresh") {
    return <span className="data-date">資料截至 {dataThrough}</span>;
  }
  return <span className="data-date">正在核對資料鮮度…</span>;
}
