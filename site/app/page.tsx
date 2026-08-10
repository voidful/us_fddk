import type { Metadata } from "next";
import PublicDecisionPage from "./PublicDecisionPage";

export const metadata: Metadata = {
  title: "美股交易參考｜只顯示已驗證策略",
  description:
    "只呈列完整通過事前、成本、風險及前瞻驗證的美股策略與今日行動；未通過結果保留在研究日誌。",
};

export default function Home() {
  return <PublicDecisionPage />;
}
