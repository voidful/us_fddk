import type { Metadata } from "next";
import PublicDecisionPage from "./PublicDecisionPage";

export const metadata: Metadata = {
  title: "美股交易參考｜只顯示已驗證策略",
  description:
    "首頁只呈列已驗證、可執行的美股策略與今日行動；完整研究記錄另存於 GitHub。",
};

export default function Home() {
  return <PublicDecisionPage />;
}
