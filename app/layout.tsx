import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://growth-guard-tw.voidful819957.chatgpt.site"),
  title: {
    default: "成長守門員 v2｜Paper-only 美股 ETF 研究",
    template: "%s｜成長守門員",
  },
  description: "20 年凍結回測顯示降回撤有效，但被動 90/10 曝險控制未通過；目前僅供 LIVE paper 研究。",
  openGraph: {
    title: "成長守門員 v2｜降回撤有效，不等於穩健超額",
    description: "勝過 SPY，但未穩定勝過被動 90% QQQ／10% SHY；目前只做 LIVE paper，不作實金照單訊號。",
    locale: "zh_TW",
    type: "website",
    images: [{ url: "/og.png", width: 1731, height: 909, alt: "成長守門員 v2 Paper-only 風險管理研究" }],
  },
  twitter: { card: "summary_large_image", images: ["/og.png"] },
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f2efe7",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="zh-Hant"
      data-signal-freshness="checking"
      data-refresh-due={data.freshness.refresh_due_at_utc}
      suppressHydrationWarning
    >
      <body>{children}</body>
    </html>
  );
}
