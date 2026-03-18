import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: 'swap' });

export const metadata: Metadata = {
  title: "ImmersiveRAG | Shared Context Service",
  description: "Next.js Console for configuring and querying local corporate vector layers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.className} antialiased bg-slate-950 text-slate-100 selection:bg-indigo-500/30 min-h-screen`}
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
