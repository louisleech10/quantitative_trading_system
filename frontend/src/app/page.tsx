import Link from "next/link";
import { Search, BarChart3, Settings, Database } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        {/* 頁面標題 */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            量化交易策略系統
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            專業的案例搜索和數據分析平台，幫助您發現市場中的交易機會
          </p>
        </div>

        {/* 功能卡片 */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          <Link href="/search" className="group">
            <div className="bg-white rounded-lg p-6 shadow-lg hover:shadow-xl transition-shadow border border-gray-200 group-hover:border-blue-300">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors">
                <Search className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">案例搜索</h3>
              <p className="text-gray-600 text-sm">
                設定搜索條件，找出符合特定模式的交易案例
              </p>
            </div>
          </Link>

          <Link href="/results" className="group">
            <div className="bg-white rounded-lg p-6 shadow-lg hover:shadow-xl transition-shadow border border-gray-200 group-hover:border-green-300">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-200 transition-colors">
                <Database className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">搜索結果</h3>
              <p className="text-gray-600 text-sm">
                查看和分析搜索到的案例數據，支持導出功能
              </p>
            </div>
          </Link>

          <Link href="/dashboard" className="group">
            <div className="bg-white rounded-lg p-6 shadow-lg hover:shadow-xl transition-shadow border border-gray-200 group-hover:border-purple-300">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-200 transition-colors">
                <BarChart3 className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">數據儀表板</h3>
              <p className="text-gray-600 text-sm">
                視覺化展示數據統計和市場分析結果
              </p>
            </div>
          </Link>

          <Link href="/settings" className="group">
            <div className="bg-white rounded-lg p-6 shadow-lg hover:shadow-xl transition-shadow border border-gray-200 group-hover:border-orange-300">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-orange-200 transition-colors">
                <Settings className="w-6 h-6 text-orange-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">系統設定</h3>
              <p className="text-gray-600 text-sm">
                配置搜索參數和系統選項
              </p>
            </div>
          </Link>
        </div>

        {/* 系統狀態 */}
        <div className="bg-white rounded-lg p-6 shadow-lg border border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">系統狀態</h2>
          <div className="grid md:grid-cols-3 gap-4">
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
          </div>
        </div>

        {/* 快速開始 */}
        <div className="text-center mt-16">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">快速開始</h2>
          <p className="text-gray-600 mb-8">
            按照以下步驟開始使用系統進行案例搜索和分析
          </p>
          <div className="flex justify-center">
            <Link 
              href="/results"
              className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              開始搜索案例
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}