'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';


interface FeatureSelectorProps {
  features: string[];
  mode: 'single' | 'multi';
  selectedFeature?: string | null;
  selectedFeatures?: string[];
  onSelectFeature?: (value: string) => void;
  onSelectFeatures?: (values: string[]) => void;
  maxMultiSelect?: number;
}


export default function FeatureSelector({
  features,
  mode,
  selectedFeature,
  selectedFeatures = [],
  onSelectFeature,
  onSelectFeatures,
  maxMultiSelect = 5,
}: FeatureSelectorProps) {
  if (mode === 'single') {
    return (
      <Select value={selectedFeature || ''} onValueChange={(value) => onSelectFeature?.(value)}>
        <SelectTrigger>
          <SelectValue placeholder="選擇特徵" />
        </SelectTrigger>
        <SelectContent>
          {features.map((feature) => (
            <SelectItem key={feature} value={feature}>
              {feature}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
      {features.map((feature) => {
        const checked = selectedFeatures.includes(feature);
        const disabled = !checked && selectedFeatures.length >= maxMultiSelect;
        return (
          <label
            key={feature}
            className="flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm text-slate-200"
          >
            <Checkbox
              checked={checked}
              disabled={disabled}
              onCheckedChange={(nextChecked) => {
                if (!onSelectFeatures) return;
                if (Boolean(nextChecked)) {
                  onSelectFeatures([...selectedFeatures, feature]);
                  return;
                }
                onSelectFeatures(selectedFeatures.filter((item) => item !== feature));
              }}
            />
            <span className="truncate">{feature}</span>
          </label>
        );
      })}
    </div>
  );
}
