import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "成長守門員｜美股 ETF 研究訊號",
    template: "%s｜成長守門員",
  },
  description: "20 年凍結回測、SPY／QQQ 比較、LIVE paper trade 與新手可讀的目標配置。",
  openGraph: {
    title: "成長守門員｜今天不用猜，照規則等下一個開盤",
    description: "20 年凍結回測與 LIVE paper trade；歷史門檻通過，統計與前瞻紀錄尚待確認。",
    locale: "zh_TW",
    type: "website",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "成長守門員美股 ETF 研究訊號" }],
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
