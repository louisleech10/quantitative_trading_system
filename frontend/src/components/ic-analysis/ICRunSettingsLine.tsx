'use client';

import { ICMethodSettings } from '@/lib/types';
import { IC_SETTING_KEYS, nonDefaultICSettingKeys } from '@/lib/icConfigOverride';
import { IC_AUTOCORR_LABEL, IC_SETTING_LABELS, settingValueLabel } from '@/components/ic-analysis/icSettingsText';

interface ICRunSettingsLineProps {
  /** 本次分析送出時之設定快照（store `runSettings`）；null ⇒ 不渲染（例：載入舊報告、尚未分析）。 */
  settings: ICMethodSettings | null;
}

/**
 * ICPERF Task 0.4 ㊸：報告頂端一行「本次設定」——列出 IC 方法、縮尾、收益率、去重（含原 VIF 篩選）、單調性門檻與
 * IC 自相關（只揭露）；非預設項標色（amber）。只一行，不另加說明文字（說明在設定面板之 ⓘ）。
 */
export default function ICRunSettingsLine({ settings }: ICRunSettingsLineProps) {
  if (!settings) {
    return null;
  }
  const changed = new Set(nonDefaultICSettingKeys(settings));
  return (
    <div className="text-xs text-slate-400 flex flex-wrap gap-x-3 gap-y-1" data-testid="ic-run-settings-line">
      <span className="text-slate-300">本次設定</span>
      {IC_SETTING_KEYS.map((key) => (
        <span
          key={key}
          data-testid={`ic-run-setting-${key}`}
          data-changed={changed.has(key) ? 'true' : 'false'}
          className={changed.has(key) ? 'text-amber-200' : undefined}
        >
          {IC_SETTING_LABELS[key]} {settingValueLabel(key, settings[key])}
        </span>
      ))}
      <span data-testid="ic-run-setting-ic_autocorrelation">{IC_AUTOCORR_LABEL} 不輸出</span>
    </div>
  );
}
