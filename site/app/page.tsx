import type { Metadata } from "next";
import PublicDecisionPage from "./PublicDecisionPage";

export const metadata: Metadata = {
  title: "美股策略狀態",
  description: "只顯示完整驗證後的策略；未通過時明確顯示今天不下單。",
};

export default function Home() {
  return <PublicDecisionPage />;
}
