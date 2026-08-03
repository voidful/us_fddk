import type { Metadata, Viewport } from "next";
import data from "../data/trading-data.json";
import "./globals.css";

const publicSiteUrl =
  process.env.PUBLIC_SITE_URL ?? "https://growth-guard-tw.voidful819957.chatgpt.site";
const publicSiteRoot = publicSiteUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(publicSiteUrl),
  title: {
    default: "成長守門員 v2｜Paper-only 美股 ETF 研究",
    template: "%s｜成長守門員",
  },
  description: "20／18／16／10 年凍結回測與跨市場比較；v20 分散器輪替只過 45/154 道經濟門檻，目前不提供實金訊號。",
  openGraph: {
    title: "成長守門員 v2｜降回撤有效，不等於穩健超額",
    description: "長期回測不等於可下單證據；v20 動態分散器輪替也未勝固定股債金，目前只做既有 LIVE paper。",
    locale: "zh_TW",
    type: "website",
    images: [{ url: `${publicSiteRoot}/og.png`, width: 1731, height: 909, alt: "成長守門員 v2 Paper-only 風險管理研究" }],
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
      lang="zh-Hant"
      data-signal-freshness="checking"
      data-refresh-due={data.freshness.refresh_due_at_utc}
      suppressHydrationWarning
    >
      <body>{children}</body>
    </html>
  );
}
