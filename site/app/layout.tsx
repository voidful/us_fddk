import type { Metadata, Viewport } from "next";
import publicDecision from "../data/public-decision.json";
import "./globals.css";

const publicSiteUrl =
  process.env.PUBLIC_SITE_URL ?? "https://voidful.github.io/us_fddk";
const publicSiteRoot = publicSiteUrl.replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(publicSiteUrl),
  title: {
    default: "美股策略狀態",
    template: "%s｜US FDDK",
  },
  description: "只顯示完整驗證後的策略；未通過時明確顯示今天不下單。",
  openGraph: {
    title: "美股策略狀態",
    description: "只有完整驗證通過的策略才會公開；否則明確顯示今天不下單。",
    locale: "zh_HK",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "美股策略狀態",
    description: "只有完整驗證通過的策略才會公開；否則明確顯示今天不下單。",
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
      data-refresh-due={publicDecision.refresh_due_at_utc}
      suppressHydrationWarning
    >
      <body>
        {children}
      </body>
    </html>
  );
}
