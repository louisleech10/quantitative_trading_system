import { create } from 'zustand';

import type {
  BatchToggleResponse,
  FeatureToggle,
  FeatureToggleListResponse,
  FeatureToggleSummaryResponse,
  FeatureToggleResponse,
} from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FeatureToggleState {
  toggles: FeatureToggle[];
  summary: FeatureToggleSummaryResponse | null;
  presets: string[];
  activePreset: string | null;
  isLoading: boolean;
  error: string | null;
  fetchToggles: (difficulty?: 'L1' | 'L2' | 'L3') => Promise<void>;
  updateToggle: (featureId: string, enabled: boolean) => Promise<void>;
  batchUpdate: (updates: Record<string, boolean>) => Promise<void>;
  applyPreset: (preset: string) => Promise<void>;
  setActivePreset: (preset: string | null) => void;
  reset: () => void;
}

function buildError(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  const payload = await response.json().catch(() => ({}));
  return new Error(payload?.detail || fallback);
}

export const useFeatureToggleStore = create<FeatureToggleState>((set, get) => ({
  toggles: [],
  summary: null,
  presets: [],
  activePreset: null,
  isLoading: false,
  error: null,
  fetchToggles: async (difficulty) => {
    set({ isLoading: true, error: null });
    try {
      const params = new URLSearchParams();
      if (difficulty) {
        params.set('difficulty', difficulty);
      }
      const query = params.toString();
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-toggles${query ? `?${query}` : ''}`);
      if (!response.ok) {
        throw await parseError(response, '載入功能開關失敗');
      }
      const payload: FeatureToggleListResponse = await response.json();
      set({
        toggles: payload.toggles,
        summary: payload.summary,
        presets: payload.presets,
      });
    } catch (error) {
      set({ error: buildError(error, '載入功能開關失敗') });
    } finally {
      set({ isLoading: false });
    }
  },
  updateToggle: async (featureId, enabled) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-toggles/${featureId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) {
        throw await parseError(response, '更新功能開關失敗');
      }
      const payload: FeatureToggleResponse = await response.json();
      const updatedToggles = get().toggles.map((item) =>
        item.feature_id === payload.toggle.feature_id ? payload.toggle : item,
      );
      set({
        toggles: updatedToggles,
        summary: payload.summary,
      });
      if (payload.cascaded.length > 0) {
        await get().fetchToggles();
      }
    } catch (error) {
      set({ error: buildError(error, '更新功能開關失敗') });
    } finally {
      set({ isLoading: false });
    }
  },
  batchUpdate: async (updates) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-toggles/batch`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      });
      if (!response.ok) {
        throw await parseError(response, '批次更新功能開關失敗');
      }
      const payload: BatchToggleResponse = await response.json();
      set({ summary: payload.summary });
      await get().fetchToggles();
    } catch (error) {
      set({ error: buildError(error, '批次更新功能開關失敗') });
    } finally {
      set({ isLoading: false });
    }
  },
  applyPreset: async (preset) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/feature-toggles/presets/${preset}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw await parseError(response, '套用 preset 失敗');
      }
      const payload: FeatureToggleListResponse = await response.json();
      set({
        toggles: payload.toggles,
        summary: payload.summary,
        presets: payload.presets,
        activePreset: preset,
      });
    } catch (error) {
      set({ error: buildError(error, '套用 preset 失敗') });
    } finally {
      set({ isLoading: false });
    }
  },
  setActivePreset: (preset) => set({ activePreset: preset }),
  reset: () =>
    set({
      toggles: [],
      summary: null,
      presets: [],
      activePreset: null,
      isLoading: false,
      error: null,
    }),
}));
