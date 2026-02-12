import type { ReactNode } from 'react';
import { Space_Grotesk } from 'next/font/google';

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-ic-sans',
});

export default function ICAnalysisLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${spaceGrotesk.variable}`}
      style={{ fontFamily: 'var(--font-ic-sans), var(--font-geist-sans), sans-serif' }}
    >
      {children}
    </div>
  );
}
