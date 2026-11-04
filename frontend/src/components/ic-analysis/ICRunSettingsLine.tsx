'use client';

import { ICMethodSettings, ICSignificanceMeta } from '@/lib/types';
import { applicableICSettingKeys, nonDefaultICSettingKeys } from '@/lib/icConfigOverride';
import { IC_SETTING_LABELS, settingValueLabel } from '@/components/ic-analysis/icSettingsText';

interface ICRunSettingsLineProps {
  /** 本次分析送出時之設定快照（store `runSettings`）；null ⇒ 不渲染（例：載入舊報告、尚未分析）。 */
  settings: ICMethodSettings | null;
  /** 本報告之分析模式（v5.58 (v)：只列該模式實際生效之設定；未給＝全部列）。 */
  mode?: string;
  /** ICPERF ㊹：報告 `metadata.significance`（選填；缺 `hac_method` ⇒ 不列顯著性段）。 */
  significance?: ICSignificanceMeta | null;
}

const rangeText = (r: [number, number] | null | undefined): string =>
  r ? (r[0] === r[1] ? `${r[0]}` : `${r[0]}–${r[1]}`) : '--';

/** ICPERF ㊹：顯著性檢定揭露一段（依 `hac_method` 分支）。 */
export function significanceSegment(sig: ICSignificanceMeta | null | undefined): string | null {
  if (!sig || !sig.hac_method) {
    return null;
  }
  const h = sig.horizon ?? '--';
  const n = rangeText(sig.n_obs_range);
  if (sig.hac_method === 'ewc_llsw2018') {
    return `顯著性 EWC（Lazarus 等 2018）h＝${h}、n＝${n}、ν＝${rangeText(sig.ewc_dof_range)}、資料不足警示 ${sig.data_warning_count ?? 0} 欄`;
  }
  return `顯著性 Newey–West 固定落後 maxlags＝${sig.maxlags ?? '--'}、h＝${h}、n＝${n}`;
}

/**
 * ICPERF Task 0.4 ㊸：報告頂端一行「本次設定」——列出 IC 方法、縮尾、收益率、去重（含原 VIF 篩選）、單調性門檻；
 * 非預設項標色（amber）。只一行，不另加說明文字（說明在設定面板之 ⓘ）。
 * v5.58 (v)：只列該分析模式實際生效之設定（跨標的模式不列縮尾、去重、單調性門檻）。
 * v5.58 (w)：IC 自相關改為報告表之欄，不再列於此行。
 * ㊹：另列顯著性檢定法（EWC 或明示 maxlags 之 Newey–West）與 h、n、ν。
 */
export default function ICRunSettingsLine({ settings, mode, significance }: ICRunSettingsLineProps) {
  if (!settings) {
    return null;
  }
  const changed = new Set(nonDefaultICSettingKeys(settings));
  const sigText = significanceSegment(significance);
  return (
    <div className="text-xs text-slate-400 flex flex-wrap gap-x-3 gap-y-1" data-testid="ic-run-settings-line">
      <span className="text-slate-300">本次設定</span>
      {applicableICSettingKeys(mode).map((key) => (
        <span
          key={key}
          data-testid={`ic-run-setting-${key}`}
          data-changed={changed.has(key) ? 'true' : 'false'}
          className={changed.has(key) ? 'text-amber-200' : undefined}
        >
          {IC_SETTING_LABELS[key]} {settingValueLabel(key, settings[key])}
        </span>
      ))}
      {sigText && <span data-testid="ic-run-setting-significance">{sigText}</span>}
    </div>
  );
}
