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
  description: "只呈列完整通過事前、成本、風險及前瞻驗證的美股策略與今日行動；未通過結果保留在研究日誌。",
  openGraph: {
    title: "美股交易參考｜只顯示已驗證策略",
    description: "只有完整通過全部門檻的策略才會公開；沒有通過時，明確顯示今天不下單。",
    locale: "zh_HK",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "美股交易參考｜只顯示已驗證策略",
    description: "只有完整通過全部門檻的策略才會公開；沒有通過時，明確顯示今天不下單。",
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
