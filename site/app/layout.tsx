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
    default: "美股交易參考｜今日行動",
    template: "%s｜US FDDK",
  },
  description: "只呈列完整通過驗證的美股策略與今日行動；沒有合格訊號時保持現金。",
  openGraph: {
    title: "美股交易參考｜今日行動",
    description: "合格策略、清晰行動；沒有合格訊號時保持現金。",
    locale: "zh_HK",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "美股交易參考｜今日行動",
    description: "合格策略、清晰行動；沒有合格訊號時保持現金。",
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
