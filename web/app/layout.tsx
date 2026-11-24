import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

// Apple devices use their own system typeface (see globals.css); Inter stands in everywhere else
const inter = Inter({ subsets: ["latin"], variable: "--f-inter", display: "swap" });

export const metadata: Metadata = {
  title: "AI Front Desk · demo by Asif",
  description: "Working demo: website leads, AI qualification, CRM, an AI voice receptionist that books visits, WhatsApp chat and comment filtering, all automated with n8n.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#eef1f7", viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
