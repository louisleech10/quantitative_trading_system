// frontend/src/store/patternStore.ts
// Pattern Discovery 狀態管理

import { create } from 'zustand';
import type { 
  Pattern, 
  XGBoostAnalysisResult, 
  PatternStatistics 
} from '@/lib/patternTypes';

interface PatternState {
  // Pattern 相關
  patterns: Pattern[];
  currentPattern: Pattern | null;
  patternStatistics: PatternStatistics | null;
  
  // XGBoost Analysis 相關
  currentAnalysis: XGBoostAnalysisResult | null;
  analysisLoading: boolean;
  analysisTaskId: string | null;
  
  // UI 狀態
  selectedPatternId: string | null;
  filters: {
    status?: string;
    tags: string[];
    case_id?: string;
  };
  
  // Actions - Pattern Management
  setPatterns: (patterns: Pattern[]) => void;
  setCurrentPattern: (pattern: Pattern | null) => void;
  setPatternStatistics: (stats: PatternStatistics | null) => void;
  selectPattern: (patternId: string | null) => void;
  addPattern: (pattern: Pattern) => void;
  updatePattern: (patternId: string, updates: Partial<Pattern>) => void;
  deletePattern: (patternId: string) => void;
  
  // Actions - XGBoost Analysis
  setCurrentAnalysis: (analysis: XGBoostAnalysisResult | null) => void;
  setAnalysisLoading: (loading: boolean) => void;
  setAnalysisTaskId: (taskId: string | null) => void;
  
  // Actions - Filters
  setFilterStatus: (status?: string) => void;
  setFilterTags: (tags: string[]) => void;
  setFilterCaseId: (caseId?: string) => void;
  clearFilters: () => void;
  
  // Computed
  getFilteredPatterns: () => Pattern[];
}

export const usePatternStore = create<PatternState>((set, get) => ({
  // Initial State
  patterns: [],
  currentPattern: null,
  patternStatistics: null,
  currentAnalysis: null,
  analysisLoading: false,
  analysisTaskId: null,
  selectedPatternId: null,
  filters: {
    status: undefined,
    tags: [],
    case_id: undefined
  },
  
  // Pattern Management Actions
  setPatterns: (patterns) => set({ patterns }),
  
  setCurrentPattern: (pattern) => set({ currentPattern: pattern }),
  
  setPatternStatistics: (stats) => set({ patternStatistics: stats }),
  
  selectPattern: (patternId) => {
    set({ selectedPatternId: patternId });
    if (patternId) {
      const pattern = get().patterns.find(p => p.pattern_id === patternId);
      set({ currentPattern: pattern || null });
    } else {
      set({ currentPattern: null });
    }
  },
  
  addPattern: (pattern) => set((state) => ({
    patterns: [pattern, ...state.patterns]
  })),
  
  updatePattern: (patternId, updates) => set((state) => ({
    patterns: state.patterns.map(p => 
      p.pattern_id === patternId ? { ...p, ...updates } : p
    ),
    currentPattern: state.currentPattern?.pattern_id === patternId 
      ? { ...state.currentPattern, ...updates } 
      : state.currentPattern
  })),
  
  deletePattern: (patternId) => set((state) => ({
    patterns: state.patterns.filter(p => p.pattern_id !== patternId),
    currentPattern: state.currentPattern?.pattern_id === patternId 
      ? null 
      : state.currentPattern,
    selectedPatternId: state.selectedPatternId === patternId 
      ? null 
      : state.selectedPatternId
  })),
  
  // XGBoost Analysis Actions
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  
  setAnalysisLoading: (loading) => set({ analysisLoading: loading }),
  
  setAnalysisTaskId: (taskId) => set({ analysisTaskId: taskId }),
  
  // Filter Actions
  setFilterStatus: (status) => set((state) => ({
    filters: { ...state.filters, status }
  })),
  
  setFilterTags: (tags) => set((state) => ({
    filters: { ...state.filters, tags }
  })),
  
  setFilterCaseId: (caseId) => set((state) => ({
    filters: { ...state.filters, case_id: caseId }
  })),
  
  clearFilters: () => set({ 
    filters: { status: undefined, tags: [], case_id: undefined }
  }),
  
  // Computed
  getFilteredPatterns: () => {
    const { patterns, filters } = get();
    
    let filtered = patterns;
    
    // 依狀態過濾
    if (filters.status) {
      filtered = filtered.filter(p => p.status === filters.status);
    }
    
    // 依標籤過濾
    if (filters.tags.length > 0) {
      filtered = filtered.filter(p => 
        filters.tags.some(tag => p.tags?.includes(tag))
      );
    }
    
    // 依案例 ID 過濾
    if (filters.case_id) {
      filtered = filtered.filter(p => 
        p.case_id.toLowerCase().includes(filters.case_id!.toLowerCase())
      );
    }
    
    return filtered;
  }
}));
