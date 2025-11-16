"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { TrainingWindowConfig } from "@/components/strategy/WindowConfigPanel";

const STORE_KEY = "strategy-config-store-v2";
const TEMPLATE_STORAGE_KEY = "strategy-test-templates-v2";

const DEFAULT_DATA_SOURCES = ["close", "volume"];

type HydrationSource = "default" | "storage" | "url";

type StrategyWindowConfig = TrainingWindowConfig & {
  far_lookback_bars?: number;
};

interface DateRange {
  start: string;
  end: string;
}

export interface StrategyFormState {
  strategyName: string;
  strategyDescription?: string;
  dataSources: string[];
  indicatorType: string;
  strategyLogic: string;
  indicatorParams: Record<string, number>;
  windowConfig: StrategyWindowConfig;
  symbol: string;
  timeframe: string;
  dateRange: DateRange;
  clusteringWeight: number;
  syncToUrl: boolean;
  templateId: string | null;
}

export interface StrategyTemplatePayload {
  id: string;
  name: string;
  description?: string;
  createdAt: number;
  updatedAt: number;
  state: StrategyFormState;
}

interface StrategyUrlPayload {
  dataSources: string[];
  indicatorType: string;
  strategyLogic: string;
  indicatorParams: Record<string, number>;
  windowConfig: StrategyWindowConfig;
  symbol: string;
  timeframe: string;
  dateRange: DateRange;
  clusteringWeight: number;
}

interface StrategyConfigStore {
  state: StrategyFormState;
  lastSyncedQuery: string | null;
  lastHydrationSource: HydrationSource;
  isHydrated: boolean;
  setField: <K extends keyof StrategyFormState>(
    key: K,
    value: StrategyFormState[K]
  ) => void;
  setFields: (values: Partial<StrategyFormState>) => void;
  reset: () => void;
  saveTemplate: (options: {
    name: string;
    description?: string;
  }) => StrategyTemplatePayload | null;
  loadTemplate: (template: StrategyTemplatePayload) => void;
  listTemplates: () => StrategyTemplatePayload[];
  deleteTemplate: (templateId: string) => void;
  syncToUrl: (extraParams?: Record<string, string>) => string | null;
  hydrateFromUrl: (input?: string | URLSearchParams) => boolean;
}

const formatDate = (date: Date) => date.toISOString().slice(0, 10);

const now = new Date();
const defaultStart = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);

const DEFAULT_STATE: StrategyFormState = {
  strategyName: "雙窗口密度測試",
  strategyDescription: "三線順勢 + 雙窗口密度",
  dataSources: DEFAULT_DATA_SOURCES,
  indicatorType: "ema",
  strategyLogic: "three_line",
  indicatorParams: {
    ema_short: 7,
    ema_mid: 18,
    ema_long: 35,
  },
  windowConfig: {
    reference_point: "TO",
    lookback_bars: 24,
    lookforward_bars: 0,
    far_lookback_bars: 100,
    mode: "relative",
  },
  symbol: "BTCUSDT",
  timeframe: "12h",
  dateRange: {
    start: formatDate(defaultStart),
    end: formatDate(now),
  },
  clusteringWeight: 0.5,
  syncToUrl: true,
  templateId: null,
};

const encodePayload = (payload: StrategyUrlPayload): string | null => {
  try {
    const json = JSON.stringify(payload);
    if (typeof window === "undefined") {
      return Buffer.from(json, "utf-8").toString("base64");
    }
    return window.btoa(encodeURIComponent(json));
  } catch (error) {
    console.error("策略配置序列化失敗", error);
    return null;
  }
};

const decodePayload = (encoded: string): StrategyUrlPayload | null => {
  try {
    const json =
      typeof window === "undefined"
        ? Buffer.from(encoded, "base64").toString("utf-8")
        : decodeURIComponent(window.atob(encoded));
    return JSON.parse(json) as StrategyUrlPayload;
  } catch (error) {
    console.error("策略配置反序列化失敗", error);
    return null;
  }
};

const buildUrlPayload = (state: StrategyFormState): StrategyUrlPayload => ({
  dataSources: state.dataSources,
  indicatorType: state.indicatorType,
  strategyLogic: state.strategyLogic,
  indicatorParams: state.indicatorParams,
  windowConfig: state.windowConfig,
  symbol: state.symbol,
  timeframe: state.timeframe,
  dateRange: state.dateRange,
  clusteringWeight: state.clusteringWeight,
});

const mergeFromPayload = (
  original: StrategyFormState,
  payload: StrategyUrlPayload
): StrategyFormState => ({
  ...original,
  dataSources: payload.dataSources ?? original.dataSources,
  indicatorType: payload.indicatorType ?? original.indicatorType,
  strategyLogic: payload.strategyLogic ?? original.strategyLogic,
  indicatorParams: {
    ...original.indicatorParams,
    ...payload.indicatorParams,
  },
  windowConfig: {
    ...original.windowConfig,
    ...payload.windowConfig,
  },
  symbol: payload.symbol ?? original.symbol,
  timeframe: payload.timeframe ?? original.timeframe,
  dateRange: payload.dateRange ?? original.dateRange,
  clusteringWeight: payload.clusteringWeight ?? original.clusteringWeight,
  templateId: null,
});

const extractEncodedState = (
  input?: string | URLSearchParams
): string | null => {
  if (input instanceof URLSearchParams) {
    return input.get("state");
  }

  if (typeof input === "string" && input.length > 0) {
    if (input.includes("=")) {
      const params = new URLSearchParams(
        input.startsWith("?") ? input : `?${input}`
      );
      return params.get("state");
    }
    return input;
  }

  if (typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    return params.get("state");
  }

  return null;
};

const readTemplatesFromStorage = (): StrategyTemplatePayload[] => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(TEMPLATE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StrategyTemplatePayload[]) : [];
  } catch (error) {
    console.error("讀取策略範本失敗", error);
    return [];
  }
};

const writeTemplatesToStorage = (templates: StrategyTemplatePayload[]) => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      TEMPLATE_STORAGE_KEY,
      JSON.stringify(templates)
    );
  } catch (error) {
    console.error("寫入策略範本失敗", error);
  }
};

export const useStrategyConfig = create<StrategyConfigStore>()(
  persist(
    (set, get) => ({
      state: DEFAULT_STATE,
      lastSyncedQuery: null,
      lastHydrationSource: "default",
      isHydrated: false,
      setField: (key, value) =>
        set((current) => ({
          state: {
            ...current.state,
            [key]: value,
          },
        })),
      setFields: (values) =>
        set((current) => ({
          state: {
            ...current.state,
            ...values,
          },
        })),
      reset: () =>
        set({
          state: DEFAULT_STATE,
          lastHydrationSource: "default",
          lastSyncedQuery: null,
        }),
      saveTemplate: ({ name, description }) => {
        if (!name.trim()) {
          console.warn("範本名稱不得為空");
          return null;
        }
        const snapshot = get().state;
        const template: StrategyTemplatePayload = {
          id: `tpl_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          name: name.trim(),
          description: description?.trim(),
          createdAt: Date.now(),
          updatedAt: Date.now(),
          state: snapshot,
        };
        const existing = readTemplatesFromStorage();
        writeTemplatesToStorage([...existing, template]);
        set((current) => ({
          state: {
            ...current.state,
            templateId: template.id,
          },
        }));
        return template;
      },
      loadTemplate: (template) =>
        set({
          state: {
            ...template.state,
            templateId: template.id,
          },
          lastHydrationSource: "storage",
          isHydrated: true,
        }),
      listTemplates: () => readTemplatesFromStorage(),
      deleteTemplate: (templateId) => {
        const currentTemplates = readTemplatesFromStorage();
        const filtered = currentTemplates.filter((tpl) => tpl.id !== templateId);
        writeTemplatesToStorage(filtered);
        set((current) => ({
          state: {
            ...current.state,
            templateId:
              current.state.templateId === templateId
                ? null
                : current.state.templateId,
          },
        }));
      },
      syncToUrl: (extraParams = {}) => {
        if (!get().state.syncToUrl) return null;
        const payload = buildUrlPayload(get().state);
        const encoded = encodePayload(payload);
        if (!encoded) return null;
        const params = new URLSearchParams(extraParams);
        params.set("state", encoded);
        const query = params.toString();
        set({
          lastSyncedQuery: query,
        });
        return `?${query}`;
      },
      hydrateFromUrl: (input) => {
        const encoded = extractEncodedState(input);
        if (!encoded) return false;
        const payload = decodePayload(encoded);
        if (!payload) return false;
        set((current) => ({
          state: mergeFromPayload(current.state, payload),
          lastHydrationSource: "url",
          isHydrated: true,
        }));
        return true;
      },
    }),
    {
      name: STORE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (store) => ({
        state: store.state,
        lastSyncedQuery: store.lastSyncedQuery,
        lastHydrationSource: store.lastHydrationSource,
        isHydrated: store.isHydrated,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error("策略狀態恢復失敗", error);
          return;
        }
        if (state) {
          state.lastHydrationSource = "storage";
          state.isHydrated = true;
        }
      },
    }
  )
);
