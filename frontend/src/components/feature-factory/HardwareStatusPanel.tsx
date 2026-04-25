'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, Cpu, RefreshCw, Server } from 'lucide-react';

interface HardwareInfo {
  memory_tier: string;
  cpu: {
    logical_cores: number;
    physical_cores: number;
    usage_pct: number;
  };
  memory: {
    total_gb: number;
    available_gb: number;
    used_pct: number;
  };
  disk: {
    path: string;
    free_gb: number;
    total_gb: number;
    used_pct: number;
  };
  recommended_settings: {
    FFACT_L65_WORKERS: number;
    FFACT_CGSA_MEMORY_BUFFER: number;
    FFACT_L7_WORKERS: number;
    FFACT_L7_COMPACTOR_ENABLED: number;
    FFACT_MULTI_TF_MAX_WORKERS: number;
    FFACT_LAYER3_CHUNK_SIZE: number;
  };
}

function getMemoryTextColor(availableGb: number): string {
  if (availableGb < 1) {
    return 'text-rose-300';
  }
  if (availableGb < 2) {
    return 'text-amber-300';
  }
  return 'text-emerald-300';
}

function getDiskTextColor(freeGb: number): string {
  if (freeGb < 5) {
    return 'text-rose-300';
  }
  if (freeGb < 10) {
    return 'text-amber-300';
  }
  return 'text-slate-200';
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 rounded bg-white/10" />
      <div className="h-4 rounded bg-white/10" />
      <div className="h-4 rounded bg-white/10" />
      <div className="h-10 rounded bg-white/10" />
    </div>
  );
}

export function HardwareStatusPanel() {
  const [hardwareInfo, setHardwareInfo] = useState<HardwareInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);

  const loadHardwareInfo = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/config/hardware', {
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as HardwareInfo;
      setHardwareInfo(data);
    } catch {
      setHardwareInfo(null);
      setError('無法取得系統資訊');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHardwareInfo();
  }, [loadHardwareInfo]);

  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => setIsExpanded((current) => !current)}
          className="flex items-center gap-3 text-left"
        >
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-cyan-200">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-medium text-slate-100">系統資源</div>
            <div className="text-xs text-slate-400">
              {hardwareInfo ? `Tier: ${hardwareInfo.memory_tier.toUpperCase()}` : '讀取硬體資訊中'}
            </div>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </button>

        <button
          type="button"
          onClick={loadHardwareInfo}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          重新整理
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {isLoading ? (
            <LoadingSkeleton />
          ) : error ? (
            <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : hardwareInfo ? (
            <>
              {/* 硬體概況：三格縮小版 */}
              <div className="grid gap-2 md:grid-cols-3">
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <Cpu className="h-4 w-4 shrink-0 text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-200">
                      {hardwareInfo.cpu.logical_cores} 核（{hardwareInfo.cpu.physical_cores} 實體）
                    </div>
                    <div className="text-xs text-slate-500">使用率 {hardwareInfo.cpu.usage_pct}%</div>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <div className="h-4 w-4 shrink-0 text-slate-400 text-xs font-bold leading-4">RAM</div>
                  <div>
                    <div className="text-xs text-slate-200">{hardwareInfo.memory.total_gb.toFixed(1)} GB</div>
                    <div className={`text-xs ${getMemoryTextColor(hardwareInfo.memory.available_gb)}`}>
                      可用 {hardwareInfo.memory.available_gb.toFixed(1)} GB · 已用 {hardwareInfo.memory.used_pct}%
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <div className="h-4 w-4 shrink-0 text-slate-400 text-xs font-bold leading-4">SSD</div>
                  <div>
                    <div className="text-xs text-slate-200">{hardwareInfo.disk.total_gb.toFixed(1)} GB</div>
                    <div className={`text-xs ${getDiskTextColor(hardwareInfo.disk.free_gb)}`}>
                      可用 {hardwareInfo.disk.free_gb.toFixed(1)} GB · 已用 {hardwareInfo.disk.used_pct}%
                    </div>
                  </div>
                </div>
              </div>

              {/* 建議設定（目前 tier 高亮） */}
              <div className="rounded-xl border border-cyan-300/20 bg-cyan-400/10 px-4 py-3">
                <div className="text-xs uppercase tracking-[0.18em] text-cyan-100/70">建議設定</div>
                <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-cyan-50">
                  <span>L65_WORKERS={hardwareInfo.recommended_settings.FFACT_L65_WORKERS}</span>
                  <span>L7_WORKERS={hardwareInfo.recommended_settings.FFACT_L7_WORKERS}</span>
                  <span>CGSA_BUFFER={hardwareInfo.recommended_settings.FFACT_CGSA_MEMORY_BUFFER}</span>
                  <span>Compactor={hardwareInfo.recommended_settings.FFACT_L7_COMPACTOR_ENABLED === 1 ? 'ON' : 'OFF'}</span>
                  <span className="text-cyan-200">MultiTF_Workers={hardwareInfo.recommended_settings.FFACT_MULTI_TF_MAX_WORKERS}</span>
                  <span className="text-cyan-200">L3_Chunk={hardwareInfo.recommended_settings.FFACT_LAYER3_CHUNK_SIZE}</span>
                </div>
              </div>

              {/* Tier 對照表 */}
              <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                <div className="px-3 py-2 text-xs uppercase tracking-[0.18em] text-slate-500 border-b border-white/10">
                  各 Tier 參數對照
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-3 py-2 text-left font-medium text-slate-400">參數</th>
                        {(['8gb', '16gb', '24gb', '32gb'] as const).map((tier) => (
                          <th
                            key={tier}
                            className={`px-3 py-2 text-center font-medium ${
                              hardwareInfo.memory_tier === tier
                                ? 'text-cyan-300 bg-cyan-400/10'
                                : 'text-slate-400'
                            }`}
                          >
                            {tier.toUpperCase()}
                            {hardwareInfo.memory_tier === tier && (
                              <span className="ml-1 text-cyan-400">◀</span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {[
                        { label: 'L65_WORKERS', values: [4, 6, 8, 8] },
                        { label: 'L7_WORKERS', values: [4, 6, 8, 8] },
                        { label: 'CGSA_BUFFER', values: [0, 0, 32, 64] },
                        { label: 'MultiTF_Workers', values: [2, 3, 4, 4], highlight: true },
                        { label: 'L3_Chunk', values: [256, 512, 512, 1024], highlight: true },
                        { label: 'Chunk_Bars', values: ['50K', '100K', '250K', '∞'] },
                      ].map(({ label, values, highlight }) => (
                        <tr key={label} className="hover:bg-white/5">
                          <td className={`px-3 py-1.5 font-mono ${highlight ? 'text-cyan-200' : 'text-slate-300'}`}>
                            {label}
                          </td>
                          {values.map((val, i) => {
                            const tier = ['8gb', '16gb', '24gb', '32gb'][i];
                            const isCurrent = hardwareInfo.memory_tier === tier;
                            return (
                              <td
                                key={tier}
                                className={`px-3 py-1.5 text-center font-mono ${
                                  isCurrent
                                    ? 'text-cyan-300 font-semibold bg-cyan-400/10'
                                    : 'text-slate-400'
                                }`}
                              >
                                {String(val)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default HardwareStatusPanel;