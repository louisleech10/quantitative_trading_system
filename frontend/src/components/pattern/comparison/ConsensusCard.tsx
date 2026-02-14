import React from 'react';

interface ConsensusCardProps {
  consensusRate: number;
  spearman: number;
}

export default function ConsensusCard({ consensusRate, spearman }: ConsensusCardProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
        <div className="text-sm text-slate-400">🔄 預測共識率</div>
        <div className="text-xl font-semibold text-slate-100">{(consensusRate * 100).toFixed(1)}%</div>
      </div>
      <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
        <div className="text-sm text-slate-400">📈 Spearman</div>
        <div className="text-xl font-semibold text-slate-100">{spearman.toFixed(3)}</div>
      </div>
    </div>
  );
}
