'use client';

import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PENDING_FEATURES } from '@/lib/pendingFeatures';

/**
 * /pending-features — 前端待補完占位頁（不遺忘機制；使用者 2026-08-19 裁定）。
 * 權威文字住 docs/IC_QUANT_GAP_REGISTRY.md；本頁只呈現摘要與建議階段；vitest 機檢與 registry 一致。
 */
export default function PendingFeaturesPage() {
  return (
    <div className="space-y-6" data-testid="pending-features-page">
      <Card>
        <CardHeader>
          <CardTitle>前端待補完（占位）</CardTitle>
          <CardDescription>
            這些功能後端／契約已到位或已裁定延後，前端刻意先不做；每項寫「為何現在不做」（三值：blocked-by／user-ruling／needs-research）、
            建議施作階段與觸發條件。權威登記處＝ <code>docs/IC_QUANT_GAP_REGISTRY.md</code>；本頁與 registry 由測試機檢一致。
          </CardDescription>
        </CardHeader>
      </Card>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-300">
            <tr>
              <th className="px-2 py-2">ID</th>
              <th className="px-2 py-2">功能</th>
              <th className="px-2 py-2">為何現在不做</th>
              <th className="px-2 py-2">建議施作階段</th>
              <th className="px-2 py-2">觸發條件</th>
              <th className="px-2 py-2">將出現在</th>
            </tr>
          </thead>
          <tbody>
            {PENDING_FEATURES.map((f) => (
              <tr key={f.registryId} id={f.registryId} className="border-t border-slate-800/60 align-top" data-testid={`pending-row-${f.registryId}`}>
                <td className="px-2 py-2 font-mono text-xs">{f.registryId}</td>
                <td className="px-2 py-2">{f.title}</td>
                <td className="px-2 py-2 text-slate-300">
                  <span className="mr-1 rounded bg-slate-700/60 px-1 text-[11px]">{f.kind}</span>
                  {f.why}
                </td>
                <td className="px-2 py-2 text-slate-300">{f.suggestedPhase}</td>
                <td className="px-2 py-2 text-slate-300">{f.trigger}</td>
                <td className="px-2 py-2 text-slate-400">{f.location}<div className="text-[11px] text-slate-500">{f.registryAnchor}</div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
