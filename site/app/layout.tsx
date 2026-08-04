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
  description: "長線 ETF 分散策略與短線研究分頁呈列；短線第二十一輪完成五條供應商、十四項正式能力的補缺矩陣，沒有路徑合格，正式就緒仍為 1/18。",
  openGraph: {
    title: "美股雙策略研究｜穩定與進取分開驗證",
    description: "長線維持 Paper-only；短線五條供應商路徑 0/5 合格，十五項替代攻擊全拒收，正式策略運行 0，實金動作 US$0。",
    locale: "zh_HK",
    type: "website",
    images: [
      {
        url: `${publicSiteRoot}/og.png`,
        width: 1731,
        height: 909,
        alt: "US FDDK 美股雙策略研究：長線 Paper-only，短線正式就緒 1/18",
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
