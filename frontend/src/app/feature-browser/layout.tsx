import { ReactNode } from 'react';


export default function FeatureBrowserLayout({ children }: { children: ReactNode }) {
  return <div className="h-full">{children}</div>;
}
