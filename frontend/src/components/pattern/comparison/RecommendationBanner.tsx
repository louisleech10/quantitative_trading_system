import React from 'react';

interface RecommendationBannerProps {
  recommendedEngine: string;
  reason: string;
}

export default function RecommendationBanner({ recommendedEngine, reason }: RecommendationBannerProps) {
  return (
    <div className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 p-4">
      <div className="text-emerald-100 font-medium">💡 推薦引擎: {recommendedEngine}</div>
      <div className="text-sm text-slate-300 mt-1">原因: {reason}</div>
    </div>
  );
}
