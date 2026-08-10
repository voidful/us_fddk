import type { Metadata } from "next";
import PublicDecisionPage from "./PublicDecisionPage";

export const metadata: Metadata = {
  title: "美股交易參考｜今日行動",
  description:
    "只呈列完整通過驗證的美股策略與今日行動；沒有合格訊號時保持現金。",
};

export default function Home() {
  return <PublicDecisionPage />;
}
