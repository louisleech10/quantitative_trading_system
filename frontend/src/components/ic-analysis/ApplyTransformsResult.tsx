/**
 * ICPOSTLEAK Task 2.2（docs/ICPOSTLEAK_SPEC.md）：IC 頁「套用後處理」結果區。
 * 自 `app/ic-analysis/page.tsx` 結果區抽出；`excluded_features` 非空時列出被排除之欄名與原因，空或缺時不渲染該段。
 */

export interface ExcludedFeature {
  name: string;
  reason: string;
}

export interface ApplyTransformsResultData {
  selected_feature_count: number;
  output_rows: number;
  output_cols: number;
  transforms_applied: string[];
  output_path?: string;
  excluded_features?: ExcludedFeature[];
}

export default function ApplyTransformsResult({ result }: { result: ApplyTransformsResultData }) {
  const excluded = result.excluded_features ?? [];
  return (
    <span className="text-xs text-emerald-300 flex flex-col gap-0.5">
      <span>
        ✓ 完成 <strong>{result.selected_feature_count}</strong> 個特徵 ·{' '}
        {result.output_rows} 行 · {result.output_cols} 欄
      </span>
      <span>套用：{result.transforms_applied.join(' → ')}</span>
      {result.output_path && (
        <span className="text-slate-400 text-[10px] break-all">{result.output_path}</span>
      )}
      {excluded.length > 0 && (
        <span className="text-amber-300 flex flex-col gap-0.5">
          <span>已排除之特徵（{excluded.length} 個，未轉換、未寫入輸出）：</span>
          {excluded.map((item) => (
            <span key={item.name} className="text-[10px] break-all">
              {item.name}（{item.reason}）
            </span>
          ))}
        </span>
      )}
    </span>
  );
}
