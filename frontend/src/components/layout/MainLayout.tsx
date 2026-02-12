// frontend/src/components/layout/MainLayout.tsx
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Search,
  BarChart3,
  Settings,
  Database,
  Menu,
  X,
  Home,
  LineChart,
  Target,
  TrendingUp
} from 'lucide-react';

interface MainLayoutProps {
  children: React.ReactNode;
}

const navigationItems = [
  {
    name: '首頁',
    href: '/',
    icon: Home,
    description: '系統概覽和快速導航'
  },
  {
    name: '案例搜索',
    href: '/search',
    icon: Search,
    description: '設定條件搜索交易案例'
  },
  {
    name: '數據準備',
    href: '/data-preparation',
    icon: Database,
    description: '上傳案例CSV並批量下載K線'
  },
  {
    name: '特徵工廠',
    href: '/feature-factory',
    icon: Database,
    description: '建立特徵組合與產生設定'
  },
  {
    name: '圖表查看',
    href: '/charts',
    icon: LineChart,
    description: '查看案例K線圖表和技術指標'
  },
  {
    name: '策略測試',
    href: '/strategy-test',
    icon: Target,
    description: '配置策略參數並進行回測（Phase 3.3）'
  },
  {
    name: '優化結果',
    href: '/optimization-result',
    icon: TrendingUp,
    description: '查看參數優化結果（Phase 3.6）'
  },
  {
    name: '模式發現',
    href: '/patterns',
    icon: Target,
    description: 'XGBoost 模式分析與管理（Phase 4）'
  },
  {
    name: 'IC 分析',
    href: '/ic-analysis',
    icon: BarChart3,
    description: 'IC Gatekeeper 分析與篩選'
  },
  {
    name: '系統設定',
    href: '/settings',
    icon: Settings,
    description: '配置系統參數'
  }
];

export default function MainLayout({ children }: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <div className="h-screen flex bg-[#0A0F1C]">
      {/* 左側導航 - 桌面版 */}
      <div className="hidden lg:flex lg:flex-col lg:w-64 lg:bg-[#1a233a]/40 lg:backdrop-blur-xl lg:border-r lg:border-white/10">
        {/* Logo 區域 */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-white/10">
          <h1 className="text-xl font-medium text-slate-100">交易策略系統</h1>
        </div>

        {/* 導航選單 */}
        <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`
                  group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200
                  ${isActive(item.href)
                    ? 'bg-blue-400/10 text-blue-400 border-r-2 border-blue-400'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                  }
                `}
              >
                <Icon 
                  className={`
                    mr-3 h-5 w-5 flex-shrink-0
                    ${isActive(item.href) ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-400'}
                  `}
                />
                <div className="flex-1">
                  <div className={`font-medium ${isActive(item.href) ? 'text-blue-400' : ''}`}>
                    {item.name}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                    {item.description}
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* 底部狀態 */}
        <div className="flex-shrink-0 px-4 py-4 border-t border-white/10">
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
            <span className="text-sm text-slate-400">系統在線</span>
          </div>
        </div>
      </div>

      {/* 移動端側邊欄覆蓋層 */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div 
            className="fixed inset-0 bg-black/60"
            onClick={() => setSidebarOpen(false)}
          />
          
          {/* 移動端側邊欄 */}
          <div className="relative flex flex-col w-64 max-w-xs bg-[#1a233a] backdrop-blur-xl h-full shadow-xl">
            {/* 關閉按鈕 */}
            <div className="absolute top-0 right-0 -mr-12 pt-2">
              <button
                className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                onClick={() => setSidebarOpen(false)}
              >
                <X className="h-6 w-6 text-white" />
              </button>
            </div>

            {/* Logo 區域 */}
            <div className="flex-shrink-0 px-6 py-4 border-b border-white/10">
              <h1 className="text-xl font-medium text-slate-100">交易策略系統</h1>
            </div>

            {/* 導航選單 */}
            <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`
                      group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200
                      ${isActive(item.href)
                        ? 'bg-blue-400/10 text-blue-400 border-r-2 border-blue-400'
                        : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                      }
                    `}
                  >
                    <Icon 
                      className={`
                        mr-3 h-5 w-5 flex-shrink-0
                        ${isActive(item.href) ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-400'}
                      `}
                    />
                    <div className="flex-1">
                      <div className={`font-medium ${isActive(item.href) ? 'text-blue-400' : ''}`}>
                        {item.name}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                        {item.description}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </nav>

            {/* 底部狀態 */}
            <div className="flex-shrink-0 px-4 py-4 border-t border-white/10">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
                <span className="text-sm text-slate-400">系統在線</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 主要內容區域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 頂部導航欄 - 移動端 */}
        <div className="lg:hidden bg-[#1a233a]/60 backdrop-blur-xl border-b border-white/10 px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-medium text-slate-100">交易策略系統</h1>
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-400"
            >
              <Menu className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* 內容區域 */}
        <main className="flex-1 overflow-auto bg-transparent">
          <div className="h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}