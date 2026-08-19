'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { findPendingFeature } from '@/lib/pendingFeatures';

/**
 * 占位殼（不遺忘機制）：放在功能將來會出現的位置；寫為何殘留／建議施作階段，點了跳 /pending-features#<id>。
 * registryId 不在清單 ⇒ 不渲染（殘留收掉後只要刪資料條目即可）。
 */
export default function PendingFeatureCard({ registryId }: { registryId: string }) {
  const item = findPendingFeature(registryId);
  if (!item) return null;
  return (
    <Card
      data-testid={`pending-feature-${registryId}`}
      className="border-dashed border-slate-500/50 bg-slate-800/30 text-slate-300"
    >
      <CardHeader>
        <CardTitle className="text-sm text-slate-200">
          ⏳ 尚未接線：{item.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-xs">
        <p>
          <span className="text-slate-400">為何現在不做（{item.kind}）：</span>
          {item.why}
        </p>
        <p>
          <span className="text-slate-400">建議施作階段：</span>
          {item.suggestedPhase}
        </p>
        <p>
          <span className="text-slate-400">觸發條件：</span>
          {item.trigger}
        </p>
        <Link href={`/pending-features#${encodeURIComponent(item.registryId)}`} className="text-sky-300 underline">
          查看全部待補完項（{item.registryId}）
        </Link>
      </CardContent>
    </Card>
  );
}
