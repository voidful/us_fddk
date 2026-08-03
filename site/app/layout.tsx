import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";
import MotionEffects from "./MotionEffects";

const publicSiteUrl =
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk";
const publicSiteRoot = publicSiteUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(publicSiteUrl),
  title: {
    default: "美股成長＋黃金策略｜最新研究及 Paper 儀表板",
    template: "%s｜US FDDK",
  },
  description: "最新 v25 80% VUG／20% GLD 的 20 年回測、三產品路徑、成本與統計測試、市場狀況及 Paper Trading 進度。",
  openGraph: {
    title: "美股成長＋黃金策略｜20 年完整研究報告",
    description: "最新策略的回測、產品敏感度、成本壓力、滾動窗口、統計診斷與前瞻 Paper 狀態，一頁完整呈列。",
    locale: "zh_HK",
    type: "website",
    images: [{ url: `${publicSiteRoot}/og.png`, width: 1730, height: 909, alt: "US FDDK 美股成長加黃金最新研究報告" }],
  },
  twitter: { card: "summary_large_image", images: [`${publicSiteRoot}/og.png`] },
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
        <MotionEffects />
        {children}
      </body>
    </html>
  );
}
