// frontend/src/components/layout/MainLayout.tsx
'use client';

import { useEffect, useState } from 'react';
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
  Brain,
  Star,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import WatchlistPanel from '@/components/common/WatchlistPanel';
import { useWatchlistStore } from '@/store/watchlistStore';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  badge?: string;
}

interface MainLayoutProps {
  children: React.ReactNode;
}

const navigationItems: NavItem[] = [
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
    href: '/charts',
    icon: LineChart,
    description: '查看案例K線圖表和技術指標'
  },
  {
    name: '特徵工廠',
    href: '/feature-factory',
    icon: Database,
    description: '建立特徵組合與產生設定'
  },
  {
    name: 'IC 分析',
    href: '/ic-analysis',
    icon: BarChart3,
    description: 'IC Gatekeeper 分析與篩選'
  },
  {
    name: '模式發現',
    href: '/patterns',
    icon: Target,
    description: 'LightGBM/XGBoost 雙引擎 ML 分析（Phase 3+4）'
  },
  {
    name: '序列模型',
    href: '/lstm-model',
    icon: Brain,
    description: 'LSTM/Transformer 時序預測模型',
    badge: '待硬體升級'
  },
  {
    name: '前端待補完',
    href: '/pending-features',
    icon: Star,
    description: '需要前端但刻意先不做的殘留（為何／建議階段／觸發）'
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [watchlistOpen, setWatchlistOpen] = useState(false);
  const pathname = usePathname();
  const watchlistCount = useWatchlistStore((state) => state.entries.length);
  const hydrateFromServer = useWatchlistStore((state) => state.hydrateFromServer);

  useEffect(() => {
    void hydrateFromServer();
  }, [hydrateFromServer]);

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen bg-[#0A0F1C]">
      {/* 左側導航 - 桌面版 */}
      <div className={`hidden lg:flex lg:flex-col lg:bg-[#1a233a]/40 lg:backdrop-blur-xl lg:border-r lg:border-white/10 transition-all duration-300 ease-in-out flex-shrink-0 sticky top-0 h-screen overflow-y-auto ${sidebarCollapsed ? 'lg:w-14' : 'lg:w-56'}`}>
        {/* Logo 區域 */}
        <div className="flex-shrink-0 border-b border-white/10 flex items-center gap-2 px-2 py-3">
          <div className="w-7 h-7 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
            <BarChart3 className="w-4 h-4 text-blue-400" />
          </div>
          {!sidebarCollapsed && (
            <h1 className="text-sm font-semibold text-slate-100 truncate flex-1">交易策略系統</h1>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="flex items-center justify-center w-7 h-7 rounded-md text-slate-400 hover:text-slate-100 hover:bg-white/10 transition-colors flex-shrink-0"
            title={sidebarCollapsed ? '展開側欄' : '收合側欄'}
          >
            {sidebarCollapsed
              ? <ChevronRight className="h-4 w-4" />
              : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* 導航選單 */}
        <nav className={`flex-1 py-3 space-y-0.5 overflow-y-auto overflow-x-hidden ${sidebarCollapsed ? 'px-1.5' : 'px-2'}`}>
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const hasBadge = !!item.badge;
            return (
              <Link
                key={item.name}
                href={item.href}
                title={sidebarCollapsed ? item.name : undefined}
                className={`
                  group flex items-center rounded-lg transition-all duration-200
                  ${sidebarCollapsed ? 'justify-center px-0 py-2.5' : 'px-2.5 py-2'}
                  ${isActive(item.href)
                    ? `bg-blue-400/10 text-blue-400${sidebarCollapsed ? '' : ' border-r-2 border-blue-400'}`
                    : hasBadge
                      ? 'text-amber-400/70 hover:bg-amber-400/5 hover:text-amber-300 border border-amber-400/20'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                  }
                `}
              >
                <Icon
                  className={`
                    h-[18px] w-[18px] flex-shrink-0
                    ${sidebarCollapsed ? '' : 'mr-2.5'}
                    ${isActive(item.href) ? 'text-blue-400' : hasBadge ? 'text-amber-400/60' : 'text-slate-500 group-hover:text-slate-400'}
                  `}
                />
                {!sidebarCollapsed && (
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium truncate ${
                      isActive(item.href) ? 'text-blue-400' : hasBadge ? 'text-amber-400/80' : ''
                    }`}>
                      {item.name}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                      {item.description}
                    </div>
                  </div>
                )}
                {!sidebarCollapsed && hasBadge && (
                  <span className="ml-1 flex-shrink-0 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-400/15 text-amber-400 border border-amber-400/30 whitespace-nowrap">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* 底部：狀態 */}
        <div className={`flex-shrink-0 border-t border-white/10 ${sidebarCollapsed ? 'px-2 py-3 flex justify-center' : 'px-3 py-3'}`}>
          {!sidebarCollapsed ? (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full"></div>
              <span className="text-xs text-slate-400">系統在線</span>
            </div>
          ) : (
            <div className="w-2 h-2 bg-emerald-400 rounded-full" title="系統在線" />
          )}
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
                const hasBadge = !!item.badge;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={`
                      group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200
                      ${isActive(item.href)
                        ? 'bg-blue-400/10 text-blue-400 border-r-2 border-blue-400'
                        : hasBadge
                          ? 'text-amber-400/70 hover:bg-amber-400/5 hover:text-amber-300 border border-amber-400/20'
                          : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                      }
                    `}
                  >
                    <Icon 
                      className={`
                        mr-3 h-5 w-5 flex-shrink-0
                        ${isActive(item.href) ? 'text-blue-400' : hasBadge ? 'text-amber-400/60' : 'text-slate-500 group-hover:text-slate-400'}
                      `}
                    />
                    <div className="flex-1 min-w-0">
                      <div className={`font-medium ${
                        isActive(item.href) ? 'text-blue-400' : hasBadge ? 'text-amber-400/80' : ''
                      }`}>
                        {item.name}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                        {item.description}
                      </div>
                    </div>
                    {hasBadge && (
                      <span className="ml-1 flex-shrink-0 text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-400/15 text-amber-400 border border-amber-400/30 whitespace-nowrap">
                        {item.badge}
                      </span>
                    )}
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
      <div className="flex-1 flex flex-col min-h-screen">
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
        <main className="flex-1 bg-transparent">
          {children}
        </main>
      </div>

      <button
        type="button"
        onClick={() => setWatchlistOpen(true)}
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full border border-amber-400/40 bg-amber-500/20 px-4 py-2 text-sm text-amber-100 shadow-lg shadow-black/40 hover:bg-amber-500/30"
      >
        <Star className="h-4 w-4" />
        Watchlist
        <span className="inline-flex min-w-6 justify-center rounded-full bg-amber-300/20 px-2 py-0.5 text-xs font-semibold">
          {watchlistCount}
        </span>
      </button>

      <WatchlistPanel open={watchlistOpen} onOpenChange={setWatchlistOpen} />
    </div>
  );
}