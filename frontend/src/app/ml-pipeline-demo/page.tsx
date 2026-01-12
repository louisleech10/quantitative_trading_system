/**
 * ML Pipeline Demo Page
 * 
 * 展示 Phase 3-6 Frontend Integration 的所有新組件
 * 
 * 包含:
 * 1. TrialComparisonPanel - 比較 Trials
 * 2. TrialSelectionDialog - 選擇 Trial
 * 3. MultiIndicatorConfig - 配置多指標
 */

'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Info } from 'lucide-react';
import TrialComparisonPanel from '@/components/optimization/TrialComparisonPanel';
import TrialSelectionDialog from '@/components/optimization/TrialSelectionDialog';
import MultiIndicatorConfig from '@/components/optimization/MultiIndicatorConfig';

// 模擬數據
const mockTrials = [
  {
    number: 1,
    value: 0.7421,
    state: 'COMPLETE' as const,
    params: { short_period: 5, mid_period: 18, long_period: 55 },
    duration_seconds: 125.3,
    user_attrs: {}
  },
  {
    number: 2,
    value: 0.8012,
    state: 'COMPLETE' as const,
    params: { short_period: 6, mid_period: 20, long_period: 60 },
    duration_seconds: 132.1,
    user_attrs: {}
  },
  {
    number: 3,
    value: 0.7156,
    state: 'COMPLETE' as const,
    params: { short_period: 4, mid_period: 15, long_period: 50 },
    duration_seconds: 118.5,
    user_attrs: {}
  },
  {
    number: 5,
    value: 0.8532,
    state: 'COMPLETE' as const,
    params: { short_period: 5, mid_period: 20, long_period: 60 },
    duration_seconds: 145.2,
    user_attrs: {}
  },
  {
    number: 10,
    value: 0.7892,
    state: 'COMPLETE' as const,
    params: { short_period: 7, mid_period: 22, long_period: 65 },
    duration_seconds: 138.9,
    user_attrs: {}
  }
];

export default function MLPipelineDemoPage() {
  const [selectedTrial, setSelectedTrial] = useState<typeof mockTrials[0] | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [indicators, setIndicators] = useState<any[]>([]);

  // 從 mockTrials 提取 trial 編號
  const allTrialNumbers = mockTrials.map(t => t.number);

  const handleTrialSelect = (trialNumber: number) => {
    const trial = mockTrials.find(t => t.number === trialNumber);
    if (trial) {
      setSelectedTrial(trial);
      setDialogOpen(true);
    }
  };

  const handlePipelineSuccess = (pipelineId: string) => {
    alert(`Pipeline 創建成功！\nPipeline ID: ${pipelineId}`);
    setDialogOpen(false);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* 頁面標題 */}
        <div>
          <h1 className="text-3xl font-bold mb-2">ML Pipeline 功能展示</h1>
          <p className="text-muted-foreground">
            Phase 3-6 Frontend Integration - 所有新組件的互動示範
          </p>
        </div>

        {/* 說明訊息 */}
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>展示頁面說明</AlertTitle>
          <AlertDescription>
            這是一個示範頁面，展示新增的 ML Pipeline 配置功能。
            在實際使用中，這些組件位於「優化結果頁面」（/optimization-result/[taskId]/pipeline）。
            您需要先完成一個優化任務，才能在實際頁面中看到這些功能。
          </AlertDescription>
        </Alert>

        {/* Tab 組件展示 */}
        <Tabs defaultValue="comparison" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="comparison">Trial 比較</TabsTrigger>
            <TabsTrigger value="multi-indicator">多指標配置</TabsTrigger>
            <TabsTrigger value="info">使用說明</TabsTrigger>
          </TabsList>

          {/* Tab 1: Trial Comparison */}
          <TabsContent value="comparison" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Trial 比較面板</CardTitle>
                <CardDescription>
                  選擇多個 trials 進行比較，查看統計資訊和推薦建議
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TrialComparisonPanel
                  taskId="demo_task"
                  studyName="demo_study"
                  allTrials={allTrialNumbers}
                  onSelectTrial={handleTrialSelect}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab 2: Multi-Indicator Config */}
          <TabsContent value="multi-indicator" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>多指標配置器</CardTitle>
                <CardDescription>
                  動態新增和配置多個技術指標（EMA、RSI、MACD）
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MultiIndicatorConfig
                  value={indicators}
                  onChange={(newIndicators) => {
                    setIndicators(newIndicators);
                    console.log('Indicators changed:', newIndicators);
                  }}
                />

                {indicators.length > 0 && (
                  <div className="mt-6 p-4 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">當前配置:</h4>
                    <pre className="text-sm overflow-auto">
                      {JSON.stringify(indicators, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tab 3: 使用說明 */}
          <TabsContent value="info" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>功能說明</CardTitle>
                <CardDescription>如何在實際系統中使用這些功能</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="font-semibold text-lg mb-3">完整工作流程</h3>
                  <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                    <li>進入「策略測試」頁面，創建一個優化任務</li>
                    <li>等待優化完成（通常需要幾分鐘到幾十分鐘）</li>
                    <li>進入「優化結果」頁面查看結果</li>
                    <li>點擊右上角的「配置 Pipeline」按鈕</li>
                    <li>在新頁面中：
                      <ul className="list-disc list-inside ml-6 mt-1 space-y-1">
                        <li><strong>Tab 1 - 選擇 Trial</strong>: 使用 TrialComparisonPanel 比較 trials</li>
                        <li>點擊「選擇此 Trial」打開 TrialSelectionDialog</li>
                        <li>填寫選擇理由（必填，至少 10 字）</li>
                        <li><strong>選項 A</strong>: 直接提交（單一指標模式）</li>
                        <li><strong>選項 B</strong>: 切換到 Tab 2 配置多指標</li>
                      </ul>
                    </li>
                    <li><strong>Tab 2 - 配置指標</strong>（可選）: 使用 MultiIndicatorConfig 新增多個指標</li>
                    <li>提交後自動跳轉到 Pipeline 詳情頁</li>
                  </ol>
                </div>

                <div>
                  <h3 className="font-semibold text-lg mb-3">核心功能</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium mb-2">Trial 比較</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• 多選 trials 進行比較</li>
                        <li>• 顯示統計資訊（Mean, Std, Min, Max）</li>
                        <li>• 智能推薦最佳 trial</li>
                        <li>• CSV 匯出功能</li>
                      </ul>
                    </div>

                    <div className="p-4 bg-green-50 rounded-lg">
                      <h4 className="font-medium mb-2">Trial 選擇</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• 顯示 trial 詳細資訊</li>
                        <li>• 必填選擇理由（user_notes）</li>
                        <li>• 可選 XGBoost 調優</li>
                        <li>• 表單驗證與錯誤提示</li>
                      </ul>
                    </div>

                    <div className="p-4 bg-purple-50 rounded-lg">
                      <h4 className="font-medium mb-2">多指標配置</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• 動態新增/移除指標</li>
                        <li>• 支援 EMA、RSI、MACD</li>
                        <li>• 資料來源選擇（close/open/volume...）</li>
                        <li>• 即時預覽特徵名稱</li>
                      </ul>
                    </div>

                    <div className="p-4 bg-amber-50 rounded-lg">
                      <h4 className="font-medium mb-2">Pipeline 管理</h4>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        <li>• 單一/多指標模式切換</li>
                        <li>• 自動生成 Pipeline ID</li>
                        <li>• 儲存為 JSON 配置</li>
                        <li>• 完整審計追蹤</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-lg mb-3">API Endpoints</h3>
                  <div className="space-y-2 text-sm font-mono bg-muted p-4 rounded-lg">
                    <div><span className="text-green-600">GET</span> /api/v1/optimization/trials/compare</div>
                    <div><span className="text-blue-600">POST</span> /api/v1/ml-pipeline/create</div>
                    <div><span className="text-green-600">GET</span> /api/v1/ml-pipeline/[id]</div>
                    <div><span className="text-green-600">GET</span> /api/v1/ml-pipeline/list</div>
                  </div>
                </div>

                <div className="p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded">
                  <h4 className="font-medium text-yellow-800 mb-1">快速開始</h4>
                  <p className="text-sm text-yellow-700">
                    想要立即體驗完整功能？請前往「策略測試」頁面創建一個新的優化任務。
                    任務完成後，在優化結果頁面就能看到「配置 Pipeline」按鈕。
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Trial Selection Dialog */}
        <TrialSelectionDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          studyName="demo_study"
          selectedTrial={selectedTrial}
          strategyType="ema_three_line"
          onSuccess={handlePipelineSuccess}
        />
      </div>
    </div>
  );
}
