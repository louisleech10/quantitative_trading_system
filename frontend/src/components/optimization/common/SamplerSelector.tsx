'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface SamplerSelectorProps {
  value: string
  onChange: (value: string) => void
}

const OPTIONS = [
  { value: 'TPE', label: 'TPE' },
  { value: 'CmaEs', label: 'CmaEs' },
  { value: 'Random', label: 'Random' },
]

export default function SamplerSelector({ value, onChange }: SamplerSelectorProps) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-300">Sampler</p>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder="選擇 Sampler" />
        </SelectTrigger>
        <SelectContent>
          {OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
