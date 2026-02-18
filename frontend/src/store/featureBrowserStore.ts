import { create } from 'zustand';

import {
  FeatureOverview,
  FeatureBrowserTab,
} from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface FeatureBrowserState {
  featuresPath: string;
  overview: FeatureOverview | null;
  activeTab: FeatureBrowserTab;
  selectedFeature: string | null;
  isLoadingCatalog: boolean;
  error: string | null;
  setFeaturesPath: (path: string) => void;
  setActiveTab: (tab: FeatureBrowserTab) => void;
  setSelectedFeature: (feature: string | null) => void;
  setError: (error: string | null) => void;
  loadOverview: () => Promise<void>;
}


export const useFeatureBrowserStore = create<FeatureBrowserState>((set, get) => ({
  featuresPath: '',
  overview: null,
  activeTab: 'overview',
  selectedFeature: null,
  isLoadingCatalog: false,
  error: null,
  setFeaturesPath: (featuresPath) => set({ featuresPath }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedFeature: (selectedFeature) => set({ selectedFeature }),
  setError: (error) => set({ error }),
  loadOverview: async () => {
    const path = get().featuresPath.trim();
    if (!path) {
      set({ error: '請先輸入 features_path' });
      return;
    }

    set({ isLoadingCatalog: true, error: null });
    try {
      const query = new URLSearchParams({ features_path: path });
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-browser/overview?${query.toString()}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || response.statusText);
      }

      const payload: FeatureOverview = await response.json();
      const selectedFeature = get().selectedFeature || payload.items[0]?.feature_name || null;
      set({
        overview: payload,
        selectedFeature,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '載入特徵目錄失敗';
      set({ error: message });
    } finally {
      set({ isLoadingCatalog: false });
    }
  },
}));
