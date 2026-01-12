// frontend/src/app/page.tsx
import Link from "next/link";
import { Search, BarChart3, Settings, Database, TrendingUp, Users, Clock } from "lucide-react";

export default function Home() {
  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto">
        {/* 歡迎區域 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            歡迎使用量化交易策略系統
          </h1>
          <p className="text-lg text-gray-600">
            專業的案例搜索和數據分析平台，幫助您發現市場中的交易機會
          </p>
        </div>

        {/* 快速統計 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">總搜索次數</p>
                <p className="text-2xl font-bold text-gray-900">1,234</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">分析案例</p>
                <p className="text-2xl font-bold text-gray-900">45,678</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Clock className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">系統運行時間</p>
                <p className="text-2xl font-bold text-gray-900">99.9%</p>
              </div>
            </div>
          </div>
        </div>

        {/* 主要功能區域 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* 案例搜索 */}
          <Link href="/search" className="group">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                  <Search className="w-8 h-8 text-blue-600" />
                </div>
                <span className="text-sm text-blue-600 font-medium">開始搜索 →</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">案例搜索</h3>
              <p className="text-gray-600 mb-4">
                設定搜索條件，找出符合特定模式的交易案例，支援多種技術指標和市場條件組合
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">價格突破</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">成交量放大</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">技術指標</span>
              </div>
            </div>
          </Link>

          {/* 搜索結果 */}
          <Link href="/result" className="group">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-green-300 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                  <Database className="w-8 h-8 text-green-600" />
                </div>
                <span className="text-sm text-green-600 font-medium">查看結果 →</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">搜索結果</h3>
              <p className="text-gray-600 mb-4">
                查看和分析搜索到的案例數據，支持導出功能和統計分析
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">統計分析</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">數據導出</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">品質評估</span>
              </div>
            </div>
          </Link>

          {/* 數據儀表板 */}
          <Link href="/dashboard" className="group">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-purple-300 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors">
                  <BarChart3 className="w-8 h-8 text-purple-600" />
                </div>
                <span className="text-sm text-purple-600 font-medium">查看圖表 →</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">數據儀表板</h3>
              <p className="text-gray-600 mb-4">
                視覺化展示數據統計和市場分析結果，包含各種圖表和趨勢分析
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">K線圖表</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">統計圖</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">績效分析</span>
              </div>
            </div>
          </Link>

          {/* ML Pipeline 展示 (NEW) */}
          <Link href="/ml-pipeline-demo" className="group">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-indigo-300 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-indigo-100 rounded-lg group-hover:bg-indigo-200 transition-colors">
                  <TrendingUp className="w-8 h-8 text-indigo-600" />
                </div>
                <span className="text-sm text-indigo-600 font-medium">🆕 新功能 →</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">ML Pipeline 配置</h3>
              <p className="text-gray-600 mb-4">
                Phase 3-6 新功能：Trial 比較、多指標配置、Pipeline 創建（功能展示頁面）
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">Trial 比較</span>
                <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">多指標</span>
                <span className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">Pipeline</span>
              </div>
            </div>
          </Link>

          {/* 系統設定 */}
          <Link href="/settings" className="group">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-orange-300 transition-all duration-200">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-orange-100 rounded-lg group-hover:bg-orange-200 transition-colors">
                  <Settings className="w-8 h-8 text-orange-600" />
                </div>
                <span className="text-sm text-orange-600 font-medium">進入設定 →</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">系統設定</h3>
              <p className="text-gray-600 mb-4">
                配置搜索參數和系統選項，管理數據源和 API 連接
              </p>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">API 配置</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">數據源</span>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">系統參數</span>
              </div>
            </div>
          </Link>
        </div>

        {/* 系統狀態 */}
        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">系統狀態</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">在線</div>
              <div className="text-sm text-gray-600">API 服務</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">正常</div>
              <div className="text-sm text-gray-600">數據連接</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">就緒</div>
              <div className="text-sm text-gray-600">搜索引擎</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">100%</div>
              <div className="text-sm text-gray-600">系統可用性</div>
            </div>
          </div>
        </div>

        {/* 快速開始提示 */}
        <div className="mt-8 text-center">
          <div className="bg-blue-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">立即開始</h3>
            <p className="text-gray-600 mb-4">
              點擊左側導航欄中的「案例搜索」開始您的第一次搜索
            </p>
            <Link 
              href="/search"
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              <Search className="w-4 h-4 mr-2" />
              開始搜索案例
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}