import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";
import "./public-decision.css";

const publicSiteUrl =
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk";
const publicSiteRoot = publicSiteUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(publicSiteUrl),
  title: {
    default: "美股交易參考｜只顯示已驗證策略",
    template: "%s｜US FDDK",
  },
  description: "首頁只呈列已驗證、可執行的美股策略與今日行動；完整研究記錄另存於 GitHub。",
  openGraph: {
    title: "美股交易參考｜只顯示已驗證策略",
    description: "只有已驗證且可執行的策略才會公開；沒有可行策略時，明確顯示今天不下單。",
    locale: "zh_HK",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "美股交易參考｜只顯示已驗證策略",
    description: "只有已驗證且可執行的策略才會公開；沒有可行策略時，明確顯示今天不下單。",
  },
  icons: { icon: `${publicSiteRoot}/favicon.svg` },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f2efe7",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="zh-Hant-HK"
      data-signal-freshness="checking"
      data-refresh-due={data.freshness.refresh_due_at_utc}
      suppressHydrationWarning
    >
      <body>
        {children}
      </body>
    </html>
  );
}
