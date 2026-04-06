'use client';

import { useMemo } from 'react';
import { CrossSectionalICMatrix } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface CrossSectionalICHeatmapProps {
  data?: CrossSectionalICMatrix | null;
  maxFeatures?: number;
  maxSymbols?: number;
}

const COLOR_BAND = 0.1;

const getCellColor = (value: number | null | undefined): string => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'rgba(100, 116, 139, 0.18)';
  }

  const clamped = Math.max(-COLOR_BAND, Math.min(COLOR_BAND, value));
  const normalized = Math.abs(clamped) / COLOR_BAND;

  if (normalized < 0.12) {
    return 'rgba(100, 116, 139, 0.2)';
  }

  const alpha = 0.15 + normalized * 0.75;
  return clamped >= 0 ? `rgba(16, 185, 129, ${alpha})` : `rgba(244, 63, 94, ${alpha})`;
};

export default function CrossSectionalICHeatmap({
  data,
  maxFeatures = 30,
  maxSymbols = 30,
}: CrossSectionalICHeatmapProps) {
  const view = useMemo(() => {
    const allFeatures = data?.features || [];
    const allSymbols = data?.symbols || [];
    const matrix = data?.matrix || {};

    const features = allFeatures.slice(0, maxFeatures);
    const symbols = allSymbols.slice(0, maxSymbols);

    const signConflictFeatures: string[] = [];
    const universalFeatures: string[] = [];
    const symbolSpecificFeatures: string[] = [];

    for (const feature of features) {
      const values = symbols
        .map((symbol) => matrix?.[feature]?.[symbol])
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));

      if (values.length < 2) {
        continue;
      }

      const posCount = values.filter((value) => value > 0).length;
      const negCount = values.filter((value) => value < 0).length;
      if (posCount > 0 && negCount > 0) {
        signConflictFeatures.push(feature);
      }

      const absValues = values.map((value) => Math.abs(value));
      const sortedAbs = [...absValues].sort((a, b) => b - a);
      if (sortedAbs.length >= 2 && sortedAbs[0] >= 0.02 && sortedAbs[0] - sortedAbs[1] >= 0.02) {
        symbolSpecificFeatures.push(feature);
      }

      const sameDirection = posCount === values.length || negCount === values.length;
      const strongRatio = absValues.filter((value) => value >= 0.015).length / values.length;
      if (sameDirection && strongRatio >= 0.7) {
        universalFeatures.push(feature);
      }
    }

    return {
      features,
      symbols,
      matrix,
      signConflictFeatures,
      signConflictFeatureSet: new Set(signConflictFeatures),
      universalFeatures,
      symbolSpecificFeatures,
      allFeatureCount: allFeatures.length,
      allSymbolCount: allSymbols.length,
    };
  }, [data, maxFeatures, maxSymbols]);

  if (view.features.length === 0 || view.symbols.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cross-Sectional IC Heatmap</CardTitle>
          <CardDescription>逐 Symbol / 因子 IC 強度分布</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[240px] flex items-center justify-center text-slate-400">暫無截面 IC 熱力圖資料</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3">
          <div>
            <CardTitle className="text-base">Cross-Sectional IC Heatmap</CardTitle>
            <CardDescription>
              X 軸為因子、Y 軸為 Symbol（顯示前 {view.features.length}/{view.allFeatureCount} 因子，{view.symbols.length}/{view.allSymbolCount} Symbols）
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant="outline" className="border-emerald-400/40 text-emerald-200">
              普遍有效: {view.universalFeatures.length}
            </Badge>
            <Badge variant="outline" className="border-amber-400/40 text-amber-200">
              特定標的有效: {view.symbolSpecificFeatures.length}
            </Badge>
            <Badge variant="outline" className="border-rose-400/40 text-rose-200">
              方向衝突: {view.signConflictFeatures.length}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-auto rounded-md border border-white/10">
          <div
            className="grid gap-1 p-3"
            style={{
              gridTemplateColumns: `120px repeat(${view.features.length}, minmax(28px, 1fr))`,
            }}
          >
            <div />
            {view.features.map((feature) => (
              <div key={`head-${feature}`} className="text-[10px] text-slate-400 truncate" title={feature}>
                {feature}
              </div>
            ))}

            {view.symbols.map((symbol) => (
              <div key={`row-${symbol}`} className="contents">
                <div className="text-[10px] text-slate-300 pr-2 truncate" title={symbol}>
                  {symbol}
                </div>
                {view.features.map((feature) => {
                  const value = view.matrix?.[feature]?.[symbol];
                  const title = typeof value === 'number' && Number.isFinite(value)
                    ? `${symbol} × ${feature}: ${value.toFixed(4)}`
                    : `${symbol} × ${feature}: 無資料`;
                  const conflict = view.signConflictFeatureSet.has(feature);
                  return (
                    <div
                      key={`cell-${symbol}-${feature}`}
                      className={`h-6 rounded-sm ${conflict ? 'ring-1 ring-amber-300/30' : ''}`}
                      title={title}
                      style={{ backgroundColor: getCellColor(value) }}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
          <span>負 IC（紅）</span>
          <span>近零（灰）</span>
          <span>正 IC（綠）</span>
        </div>
      </CardContent>
    </Card>
  );
}
