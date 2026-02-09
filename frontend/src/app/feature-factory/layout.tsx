import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-ff-space",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-ff-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Feature Factory | 量化交易策略系統",
  description: "特徵工廠配置與生成管理介面",
};

export default function FeatureFactoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <section
      className={`${spaceGrotesk.variable} ${jetBrainsMono.variable} font-[var(--font-ff-space)]`}
    >
      {children}
    </section>
  );
}
