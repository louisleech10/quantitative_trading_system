'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import type { EngineMode, LightGBMConfig, ValidationConfig, XGBoostConfig } from '@/lib/patternTypes';

interface EngineConfigPanelProps {
  onEngineChange: (engine: EngineMode) => void;
  onConfigChange: (config: XGBoostConfig | LightGBMConfig) => void;
  onValidationChange: (validation: ValidationConfig) => void;
  onOptunaToggle: (enabled: boolean, nTrials: number) => void;
}

const defaultXGBoostConfig: XGBoostConfig = {
  max_depth: 6,
  learning_rate: 0.05,
  n_estimators: 100,
  subsample: 0.8,
  colsample_bytree: 0.8,
  min_child_weight: 1,
  gamma: 0,
  reg_alpha: 0,
  reg_lambda: 1
};

const defaultLightGBMConfig: LightGBMConfig = {
  boosting_type: 'gbdt',
  num_leaves: 31,
  max_depth: -1,
  learning_rate: 0.05,
  n_estimators: 200,
  subsample: 0.8,
  colsample_bytree: 0.8,
  min_child_samples: 20,
  reg_alpha: 0.1,
  reg_lambda: 1,
  min_gain_to_split: 0.01,
  categorical_features: []
};

const defaultValidation: ValidationConfig = {
  cv_folds: 5,
  purge_gap: 5,
  oot_enabled: false,
  oot_ratio: 0.2,
  early_stopping_rounds: 50
};

export default function EngineConfigPanel({
  onEngineChange,
  onConfigChange,
  onValidationChange,
  onOptunaToggle
}: EngineConfigPanelProps) {
  const [engineMode, setEngineMode] = useState<EngineMode>('xgboost');
  const [xgboostConfig, setXgboostConfig] = useState<XGBoostConfig>(defaultXGBoostConfig);
  const [lightgbmConfig, setLightgbmConfig] = useState<LightGBMConfig>(defaultLightGBMConfig);
  const [validationConfig, setValidationConfig] = useState<ValidationConfig>(defaultValidation);
  const [showValidation, setShowValidation] = useState(false);
  const [optunaEnabled, setOptunaEnabled] = useState(false);
  const [optunaTrials, setOptunaTrials] = useState(100);
  const [enableCategorical, setEnableCategorical] = useState(false);
  const lastEngineRef = useRef<EngineMode | null>(null);
  const lastConfigRef = useRef<string>('');
  const lastValidationRef = useRef<string>('');
  const lastOptunaRef = useRef<string>('');

  const activeConfig = useMemo(() => {
    if (engineMode === 'lightgbm') return lightgbmConfig;
    return xgboostConfig;
  }, [engineMode, lightgbmConfig, xgboostConfig]);

  useEffect(() => {
    if (lastEngineRef.current === engineMode) return;
    lastEngineRef.current = engineMode;
    onEngineChange(engineMode);
  }, [engineMode, onEngineChange]);

  useEffect(() => {
    const serialized = JSON.stringify(activeConfig);
    if (lastConfigRef.current === serialized) return;
    lastConfigRef.current = serialized;
    onConfigChange(activeConfig);
  }, [activeConfig, onConfigChange]);

  useEffect(() => {
    const serialized = JSON.stringify(validationConfig);
    if (lastValidationRef.current === serialized) return;
    lastValidationRef.current = serialized;
    onValidationChange(validationConfig);
  }, [validationConfig, onValidationChange]);

  useEffect(() => {
    const serialized = `${optunaEnabled}:${optunaTrials}`;
    if (lastOptunaRef.current === serialized) return;
    lastOptunaRef.current = serialized;
    onOptunaToggle(optunaEnabled, optunaTrials);
  }, [optunaEnabled, optunaTrials, onOptunaToggle]);

  useEffect(() => {
    setLightgbmConfig((prev) => ({
      ...prev,
      categorical_features: enableCategorical ? prev.categorical_features || [] : []
    }));
  }, [enableCategorical]);

  const engineButtonClass = (value: EngineMode) => {
    const active = engineMode === value;
    return active
      ? 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40'
      : 'bg-slate-900/50 text-slate-300 border-slate-700';
  };

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100">🔧 引擎 & 模型配置</CardTitle>
        <CardDescription className="text-slate-400">Step 3：選擇引擎、模型參數與驗證設定</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label className="text-slate-200 font-medium">引擎選擇</Label>
          <div className="grid grid-cols-3 gap-2">
            <Button type="button" variant="outline" className={engineButtonClass('xgboost')} onClick={() => setEngineMode('xgboost')}>XGBoost</Button>
            <Button type="button" variant="outline" className={engineButtonClass('lightgbm')} onClick={() => setEngineMode('lightgbm')}>LightGBM</Button>
            <Button type="button" variant="outline" className={engineButtonClass('both')} onClick={() => setEngineMode('both')}>雙引擎對比</Button>
          </div>
        </div>

        {(engineMode === 'xgboost' || engineMode === 'both') && (
          <div className="space-y-3 rounded-lg border border-slate-800/80 p-3 bg-slate-900/40">
            <Label className="text-slate-200">XGBoost 參數</Label>
            <div className="grid grid-cols-2 gap-3">
              <ParamInput label="max_depth" value={xgboostConfig.max_depth} onChange={(v) => setXgboostConfig((p) => ({ ...p, max_depth: v }))} />
              <ParamInput label="learning_rate" step="0.01" value={xgboostConfig.learning_rate} onChange={(v) => setXgboostConfig((p) => ({ ...p, learning_rate: v }))} />
              <ParamInput label="n_estimators" value={xgboostConfig.n_estimators} onChange={(v) => setXgboostConfig((p) => ({ ...p, n_estimators: v }))} />
              <ParamInput label="subsample" step="0.01" value={xgboostConfig.subsample} onChange={(v) => setXgboostConfig((p) => ({ ...p, subsample: v }))} />
            </div>
          </div>
        )}

        {(engineMode === 'lightgbm' || engineMode === 'both') && (
          <div className="space-y-3 rounded-lg border border-slate-800/80 p-3 bg-slate-900/40">
            <Label className="text-slate-200">LightGBM 參數</Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-slate-400">boosting_type</Label>
                <Select
                  value={lightgbmConfig.boosting_type}
                  onValueChange={(value: 'gbdt' | 'dart' | 'goss') => setLightgbmConfig((p) => ({ ...p, boosting_type: value }))}
                >
                  <SelectTrigger className="bg-slate-900/60 border-slate-700 text-slate-100"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-slate-950 border-slate-800">
                    <SelectItem value="gbdt">GBDT</SelectItem>
                    <SelectItem value="dart">DART</SelectItem>
                    <SelectItem value="goss">GOSS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <ParamInput label="num_leaves" value={lightgbmConfig.num_leaves} onChange={(v) => setLightgbmConfig((p) => ({ ...p, num_leaves: v }))} />
              <ParamInput label="learning_rate" step="0.01" value={lightgbmConfig.learning_rate} onChange={(v) => setLightgbmConfig((p) => ({ ...p, learning_rate: v }))} />
              <ParamInput label="n_estimators" value={lightgbmConfig.n_estimators} onChange={(v) => setLightgbmConfig((p) => ({ ...p, n_estimators: v }))} />
              <ParamInput label="min_child_samples" value={lightgbmConfig.min_child_samples} onChange={(v) => setLightgbmConfig((p) => ({ ...p, min_child_samples: v }))} />
              <ParamInput label="reg_alpha" step="0.01" value={lightgbmConfig.reg_alpha} onChange={(v) => setLightgbmConfig((p) => ({ ...p, reg_alpha: v }))} />
            </div>
            <div className="flex items-center gap-2 pt-1">
              <Checkbox checked={enableCategorical} onCheckedChange={(checked) => setEnableCategorical(Boolean(checked))} />
              <Label className="text-sm text-slate-300">啟用類別特徵</Label>
            </div>
          </div>
        )}

        {engineMode === 'both' && (
          <div className="rounded-lg border border-slate-800/80 p-3 bg-slate-900/40 text-sm text-slate-300 space-y-1">
            <p>✅ 使用兩引擎分別訓練並產生對比報告</p>
            <p>✅ 產出推薦引擎與指標差異</p>
          </div>
        )}

        <div className="space-y-2 rounded-lg border border-slate-800/80 p-3 bg-slate-900/40">
          <div className="flex items-center gap-2">
            <Checkbox checked={optunaEnabled} onCheckedChange={(checked) => setOptunaEnabled(Boolean(checked))} />
            <Label className="text-slate-200">啟用 Optuna 自動調參</Label>
          </div>
          {optunaEnabled && (
            <div className="grid grid-cols-2 gap-3">
              <ParamInput label="Trial 數" value={optunaTrials} onChange={(v) => setOptunaTrials(v)} />
              <div className="text-xs text-slate-400 flex items-end">目標：CV AUC 最大化</div>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <Button type="button" variant="outline" className="w-full border-slate-700 text-slate-300" onClick={() => setShowValidation((v) => !v)}>
            {showValidation ? '收合驗證配置' : '展開驗證配置'}
          </Button>
          {showValidation && (
            <div className="grid grid-cols-2 gap-3 rounded-lg border border-slate-800/80 p-3 bg-slate-900/40">
              <ParamInput label="CV 折數" value={validationConfig.cv_folds} onChange={(v) => setValidationConfig((p) => ({ ...p, cv_folds: v }))} />
              <ParamInput label="Purge Gap" value={validationConfig.purge_gap} onChange={(v) => setValidationConfig((p) => ({ ...p, purge_gap: v }))} />
              <div className="flex items-center gap-2 col-span-2">
                <Checkbox checked={validationConfig.oot_enabled} onCheckedChange={(checked) => setValidationConfig((p) => ({ ...p, oot_enabled: Boolean(checked) }))} />
                <Label className="text-sm text-slate-300">OOT 驗證</Label>
              </div>
              <ParamInput label="OOT 比例" step="0.01" value={validationConfig.oot_ratio} onChange={(v) => setValidationConfig((p) => ({ ...p, oot_ratio: v }))} />
              <ParamInput label="Early Stopping" value={validationConfig.early_stopping_rounds} onChange={(v) => setValidationConfig((p) => ({ ...p, early_stopping_rounds: v }))} />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ParamInput({
  label,
  value,
  onChange,
  step
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  step?: string;
}) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-slate-400">{label}</Label>
      <Input
        type="number"
        value={value}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-slate-900/60 border-slate-700 text-slate-100"
      />
    </div>
  );
}
