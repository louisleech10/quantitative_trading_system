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
  LineChart
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
    name: '圖表查看',
    href: '/chart',
    icon: LineChart,
    description: '查看案例K線圖表和技術指標'
  },
  {
    name: '圖表分析',
    href: '/dashboard',
    icon: BarChart3,
    description: '圖表視覺化和技術分析（Phase 2）'
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
    <div className="h-screen flex bg-gray-50">
      {/* 左側導航 - 桌面版 */}
      <div className="hidden lg:flex lg:flex-col lg:w-64 lg:bg-white lg:border-r lg:border-gray-200">
        {/* Logo 區域 */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">交易策略系統</h1>
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
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-500'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }
                `}
              >
                <Icon 
                  className={`
                    mr-3 h-5 w-5 flex-shrink-0
                    ${isActive(item.href) ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}
                  `}
                />
                <div className="flex-1">
                  <div className={`font-medium ${isActive(item.href) ? 'text-blue-700' : ''}`}>
                    {item.name}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                    {item.description}
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* 底部狀態 */}
        <div className="flex-shrink-0 px-4 py-4 border-t border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span className="text-sm text-gray-600">系統在線</span>
          </div>
        </div>
      </div>

      {/* 移動端側邊欄覆蓋層 */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div 
            className="fixed inset-0 bg-gray-600 bg-opacity-75"
            onClick={() => setSidebarOpen(false)}
          />
          
          {/* 移動端側邊欄 */}
          <div className="relative flex flex-col w-64 max-w-xs bg-white h-full shadow-xl">
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
            <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200">
              <h1 className="text-xl font-bold text-gray-900">交易策略系統</h1>
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
                        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-500'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                      }
                    `}
                  >
                    <Icon 
                      className={`
                        mr-3 h-5 w-5 flex-shrink-0
                        ${isActive(item.href) ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}
                      `}
                    />
                    <div className="flex-1">
                      <div className={`font-medium ${isActive(item.href) ? 'text-blue-700' : ''}`}>
                        {item.name}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                        {item.description}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </nav>

            {/* 底部狀態 */}
            <div className="flex-shrink-0 px-4 py-4 border-t border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                <span className="text-sm text-gray-600">系統在線</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 主要內容區域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 頂部導航欄 - 移動端 */}
        <div className="lg:hidden bg-white border-b border-gray-200 px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-lg font-semibold text-gray-900">交易策略系統</h1>
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-gray-500 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
            >
              <Menu className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* 內容區域 */}
        <main className="flex-1 overflow-auto bg-gray-50">
          <div className="h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}