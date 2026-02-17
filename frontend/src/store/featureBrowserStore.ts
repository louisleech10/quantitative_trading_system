import { create } from 'zustand';

import {
  FeatureBrowserCatalogResponse,
  FeatureBrowserTab,
} from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface FeatureBrowserState {
  featuresPath: string;
  catalog: FeatureBrowserCatalogResponse | null;
  activeTab: FeatureBrowserTab;
  selectedFeature: string | null;
  selectedFeatures: string[];
  isLoadingCatalog: boolean;
  error: string | null;
  setFeaturesPath: (path: string) => void;
  setActiveTab: (tab: FeatureBrowserTab) => void;
  setSelectedFeature: (feature: string | null) => void;
  setSelectedFeatures: (features: string[]) => void;
  setError: (error: string | null) => void;
  loadCatalog: () => Promise<void>;
}


export const useFeatureBrowserStore = create<FeatureBrowserState>((set, get) => ({
  featuresPath: '',
  catalog: null,
  activeTab: 'overview',
  selectedFeature: null,
  selectedFeatures: [],
  isLoadingCatalog: false,
  error: null,
  setFeaturesPath: (featuresPath) => set({ featuresPath }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setSelectedFeature: (selectedFeature) => set({ selectedFeature }),
  setSelectedFeatures: (selectedFeatures) => set({ selectedFeatures }),
  setError: (error) => set({ error }),
  loadCatalog: async () => {
    const path = get().featuresPath.trim();
    if (!path) {
      set({ error: '請先輸入 features_path' });
      return;
    }

    set({ isLoadingCatalog: true, error: null });
    try {
      const query = new URLSearchParams({ features_path: path });
      const response = await fetch(`${API_BASE_URL}/api/v1/features/catalog?${query.toString()}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || response.statusText);
      }

      const payload: FeatureBrowserCatalogResponse = await response.json();
      const selectedFeature = get().selectedFeature || payload.items[0]?.name || null;
      set({
        catalog: payload,
        selectedFeature,
        selectedFeatures: selectedFeature ? [selectedFeature] : [],
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '載入特徵目錄失敗';
      set({ error: message });
    } finally {
      set({ isLoadingCatalog: false });
    }
  },
}));
