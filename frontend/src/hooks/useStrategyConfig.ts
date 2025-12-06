"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { TrainingWindowConfig } from "@/components/strategy/WindowConfigPanel";

const STORE_KEY = "strategy-config-store-v2";
const TEMPLATE_STORAGE_KEY = "strategy-test-templates-v2";
const STATE_CACHE_KEY = "strategy-config-last-url-payload";

const DEFAULT_DATA_SOURCE = "close";

export type HydrationSource = "default" | "storage" | "url";

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
  dataSources: string;
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
  dataSources: string;
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
  hydrateFromCache: () => boolean;
  cacheStateSnapshot: () => string | null;
}

const formatDate = (date: Date) => date.toISOString().slice(0, 10);

const now = new Date();
const defaultStart = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);

const DEFAULT_STATE: StrategyFormState = {
  strategyName: "雙窗口密度測試",
  strategyDescription: "三線順勢 + 雙窗口密度",
  dataSources: DEFAULT_DATA_SOURCE,
  indicatorType: "ema",
  strategyLogic: "three_line",
  indicatorParams: {
    short_period: 7,
    mid_period: 25,
    long_period: 70,
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

const hasPlainParams = (params?: URLSearchParams | null): boolean => {
  if (!params) return false;
  const candidateKeys = [
    "symbol",
    "timeframe",
    "start",
    "end",
    "dataSources",
    "indicatorType",
    "strategyLogic",
    "emaShort",
    "emaMid",
    "emaLong",
    "lookback",
    "farLookback",
    "forward",
    "clusterWeight",
  ];
  return candidateKeys.some((key) => params.has(key));
};

const parsePlainQueryPayload = (
  params: URLSearchParams
): StrategyUrlPayload | null => {
  if (!hasPlainParams(params)) {
    return null;
  }

  const getNumber = (key: string): number | undefined => {
    const value = params.get(key);
    if (value === null || value === "") return undefined;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  const getDate = (key: "start" | "end", fallback: string): string => {
    const value = params.get(key);
    if (!value) return fallback;
    return value.slice(0, 10);
  };

  const dataSourcesParam = params.get("dataSources");
  const parsedDataSource = dataSourcesParam?.trim() || null;

  const indicatorParams = {
    ...DEFAULT_STATE.indicatorParams,
    short_period: getNumber("emaShort") ?? DEFAULT_STATE.indicatorParams.short_period,
    mid_period: getNumber("emaMid") ?? DEFAULT_STATE.indicatorParams.mid_period,
    long_period: getNumber("emaLong") ?? DEFAULT_STATE.indicatorParams.long_period,
  };

  const windowConfig: StrategyWindowConfig = {
    ...DEFAULT_STATE.windowConfig,
    lookback_bars:
      getNumber("lookback") ?? DEFAULT_STATE.windowConfig.lookback_bars,
    lookforward_bars:
      getNumber("forward") ?? DEFAULT_STATE.windowConfig.lookforward_bars,
    far_lookback_bars:
      getNumber("farLookback") ?? DEFAULT_STATE.windowConfig.far_lookback_bars,
  };

  const clusteringWeight = getNumber("clusterWeight");

  return {
    dataSources: parsedDataSource ?? DEFAULT_STATE.dataSources,
    indicatorType:
      params.get("indicatorType") ?? DEFAULT_STATE.indicatorType,
    strategyLogic:
      params.get("strategyLogic") ?? DEFAULT_STATE.strategyLogic,
    indicatorParams,
    windowConfig,
    symbol: params.get("symbol") ?? DEFAULT_STATE.symbol,
    timeframe: params.get("timeframe") ?? DEFAULT_STATE.timeframe,
    dateRange: {
      start: getDate("start", DEFAULT_STATE.dateRange.start),
      end: getDate("end", DEFAULT_STATE.dateRange.end),
    },
    clusteringWeight:
      typeof clusteringWeight === "number"
        ? Math.min(Math.max(clusteringWeight, 0), 1)
        : DEFAULT_STATE.clusteringWeight,
  };
};

const appendPlainQueryParams = (
  params: URLSearchParams,
  state: StrategyFormState
) => {
  const assignIfValue = (key: string, value?: string | number | null) => {
    if (value === undefined || value === null) return;
    const stringValue = typeof value === "number" ? String(value) : value;
    if (!stringValue) return;
    params.set(key, stringValue);
  };

  assignIfValue("symbol", state.symbol);
  assignIfValue("timeframe", state.timeframe);
  assignIfValue("start", state.dateRange.start);
  assignIfValue("end", state.dateRange.end);
  assignIfValue("dataSources", state.dataSources);
  assignIfValue("indicatorType", state.indicatorType);
  assignIfValue("strategyLogic", state.strategyLogic);
  assignIfValue("emaShort", state.indicatorParams.short_period);
  assignIfValue("emaMid", state.indicatorParams.mid_period);
  assignIfValue("emaLong", state.indicatorParams.long_period);
  assignIfValue("lookback", state.windowConfig.lookback_bars);
  assignIfValue("farLookback", state.windowConfig.far_lookback_bars);
  assignIfValue("forward", state.windowConfig.lookforward_bars);
  assignIfValue("clusterWeight", state.clusteringWeight);
};

const normalizeSearchParams = (
  input?: string | URLSearchParams
): { params: URLSearchParams | null; directState: string | null } => {
  if (input instanceof URLSearchParams) {
    return { params: input, directState: null };
  }

  if (typeof input === "string" && input.length > 0) {
    if (input.includes("=")) {
      const params = new URLSearchParams(
        input.startsWith("?") ? input : `?${input}`
      );
      return { params, directState: null };
    }
    return { params: null, directState: input };
  }

  if (typeof window !== "undefined") {
    return {
      params: new URLSearchParams(window.location.search),
      directState: null,
    };
  }

  return { params: null, directState: null };
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

const cacheEncodedPayload = (encoded: string) => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STATE_CACHE_KEY, encoded);
  } catch (error) {
    console.error("寫入策略快照失敗", error);
  }
};

const readCachedEncodedPayload = (): string | null => {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(STATE_CACHE_KEY);
  } catch (error) {
    console.error("讀取策略快照失敗", error);
    return null;
  }
};

const clearCachedEncodedPayload = () => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STATE_CACHE_KEY);
  } catch (error) {
    console.error("清除策略快照失敗", error);
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
        set(() => {
          clearCachedEncodedPayload();
          return {
            state: DEFAULT_STATE,
            lastHydrationSource: "default",
            lastSyncedQuery: null,
          };
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
        const snapshot = get().state;
        const payload = buildUrlPayload(snapshot);
        const encoded = encodePayload(payload);
        if (!encoded) return null;
        cacheEncodedPayload(encoded);
        const params = new URLSearchParams(extraParams);
        appendPlainQueryParams(params, snapshot);
        params.set("state", encoded);
        const query = params.toString();
        set({
          lastSyncedQuery: query,
        });
        return `?${query}`;
      },
      hydrateFromUrl: (input) => {
        const { params, directState } = normalizeSearchParams(input);
        const encoded = directState ?? params?.get("state") ?? null;

        if (encoded) {
          const payload = decodePayload(encoded);
          if (!payload) return false;
          cacheEncodedPayload(encoded);
          set((current) => ({
            state: mergeFromPayload(current.state, payload),
            lastHydrationSource: "url",
            isHydrated: true,
          }));
          return true;
        }

        if (params) {
          const plainPayload = parsePlainQueryPayload(params);
          if (plainPayload) {
            set((current) => ({
              state: mergeFromPayload(current.state, plainPayload),
              lastHydrationSource: "url",
              isHydrated: true,
            }));
            return true;
          }
        }

        return false;
      },
      hydrateFromCache: () => {
        const encoded = readCachedEncodedPayload();
        if (!encoded) return false;
        const payload = decodePayload(encoded);
        if (!payload) return false;
        set((current) => ({
          state: mergeFromPayload(current.state, payload),
          lastHydrationSource: "storage",
          isHydrated: true,
        }));
        return true;
      },
      cacheStateSnapshot: () => {
        const payload = buildUrlPayload(get().state);
        const encoded = encodePayload(payload);
        if (!encoded) return null;
        cacheEncodedPayload(encoded);
        return encoded;
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
