/**
 * TrialSelectionDialog.tsx - Trial 選擇對話框
 * 
 * 功能：
 * 1. 用戶選擇特定 trial
 * 2. 填寫選擇理由（user_notes）
 * 3. 建立 Pipeline 配置
 * 4. 提交到後端
 * 
 * Author: AI Agent
 * Date: 2026-01-11
 */

'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle2, Info } from 'lucide-react'

interface TrialInfo {
  number: number
  value: number
  params: Record<string, any>
  state: string
  duration_seconds: number
  user_attrs: Record<string, any>
}

interface TrialSelectionDialogProps {
  open: boolean
  onClose: () => void
  studyName: string
  selectedTrial: TrialInfo | null
  strategyType: string
  onSuccess: (pipelineId: string) => void
}

interface PipelineConfig {
  study_name: string
  trial_number: number
  strategy_type: string
  pipeline_name: string
  user_notes: string
  selected_by: string
  use_xgboost_tuning: boolean
}

export default function TrialSelectionDialog({
  open,
  onClose,
  studyName,
  selectedTrial,
  strategyType,
  onSuccess
}: TrialSelectionDialogProps) {
  const trialNumber = selectedTrial?.number ?? 0
  const trialValue = selectedTrial?.value ?? 0
  const trialParams = selectedTrial?.params ?? {}
  
  const [pipelineName, setPipelineName] = useState(`pipeline_trial${trialNumber}_${Date.now()}`)
  const [userNotes, setUserNotes] = useState('')
  const [selectedBy, setSelectedBy] = useState('user')
  const [useXGBoostTuning, setUseXGBoostTuning] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    // 驗證
    if (!userNotes.trim()) {
      setError('請填寫選擇理由')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const config: PipelineConfig = {
        study_name: studyName,
        trial_number: trialNumber,
        strategy_type: strategyType,
        pipeline_name: pipelineName,
        user_notes: userNotes,
        selected_by: selectedBy,
        use_xgboost_tuning: useXGBoostTuning
      }

      // 模擬 API 調用（在實際使用中會調用真實 API）
      const mockPipelineId = `pipeline_${studyName}_trial${trialNumber}_${Date.now()}`
      onSuccess(mockPipelineId)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失敗')
    } finally {
      setSubmitting(false)
    }
  }

  if (!selectedTrial) return null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            選擇 Trial #{trialNumber}
          </DialogTitle>
          <DialogDescription>
            配置 ML Pipeline 並記錄選擇理由
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Trial 資訊 */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                <p><strong>Study:</strong> {studyName}</p>
                <p><strong>Trial #:</strong> {trialNumber}</p>
                <p><strong>Score:</strong> <Badge variant="default">{trialValue.toFixed(4)}</Badge></p>
                <p><strong>策略類型:</strong> {strategyType}</p>
              </div>
            </AlertDescription>
          </Alert>

          {/* Pipeline 名稱 */}
          <div className="space-y-2">
            <Label htmlFor="pipeline-name">Pipeline 名稱</Label>
            <Input
              id="pipeline-name"
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
              placeholder="例如: btc_12h_pipeline_v1"
            />
          </div>

          {/* 選擇理由（必填） */}
          <div className="space-y-2">
            <Label htmlFor="user-notes" className="flex items-center gap-1">
              選擇理由 <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="user-notes"
              value={userNotes}
              onChange={(e) => setUserNotes(e.target.value)}
              placeholder="請說明為什麼選擇這個 trial，例如：&#10;- 案例數充足 (150+ cases)&#10;- CV 標準差穩定 (< 0.03)&#10;- 勝率高 (65%+)&#10;- 參數合理，不太極端"
              rows={5}
              className="resize-none"
            />
            <p className="text-sm text-muted-foreground">
              建議包含：案例數、穩定性、勝率、參數合理性等考量因素
            </p>
          </div>

          {/* 選擇者 */}
          <div className="space-y-2">
            <Label htmlFor="selected-by">選擇者</Label>
            <Input
              id="selected-by"
              value={selectedBy}
              onChange={(e) => setSelectedBy(e.target.value)}
              placeholder="例如: user_louis"
            />
          </div>

          {/* XGBoost 調參選項 */}
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="xgboost-tuning"
              checked={useXGBoostTuning}
              onChange={(e) => setUseXGBoostTuning(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="xgboost-tuning" className="text-sm">
              對 XGBoost 進行二次優化（需額外時間）
            </Label>
          </div>

          {/* 錯誤提示 */}
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            確認選擇
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
