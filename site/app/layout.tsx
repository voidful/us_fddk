import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";

const publicSiteUrl =
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk";
const publicSiteRoot = publicSiteUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(publicSiteUrl),
  title: {
    default: "美股雙策略研究｜長線穩定與短線高回報",
    template: "%s｜US FDDK",
  },
  description: "長線 ETF 分散策略與短線動量研究，以兩個分頁呈列 20 年回測、QQQ／SPY baseline、成本、風險、統計門檻及 Paper 狀態。",
  openGraph: {
    title: "美股雙策略研究｜穩定與進取分開驗證",
    description: "長線維持 Paper-only；短線第十輪 27/48 失敗。完整呈列 QQQ 及 SPY 比較，實金動作 US$0。",
    locale: "zh_HK",
    type: "website",
    images: [
      {
        url: `${publicSiteRoot}/og.png`,
        width: 1729,
        height: 910,
        alt: "US FDDK 美股雙策略研究：長線穩定與短線高回報",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: [`${publicSiteRoot}/og.png`],
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
