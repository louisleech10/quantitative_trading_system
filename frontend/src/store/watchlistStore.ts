import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { fetchWatchlist, syncWatchlist } from '@/lib/api/watchlistApi';
import { WatchlistEntry, WatchlistExportPayload, WatchlistStatus } from '@/lib/types';

const STORAGE_KEY = 'factor_watchlist_v1';
const MAX_WATCHLIST_ENTRIES = 500;
const SERVER_SYNC_DEBOUNCE_MS = 500;
const ALLOWED_STATUSES: WatchlistStatus[] = ['candidate', 'verified', 'rejected', 'watching'];

interface WatchlistStoreState {
  entries: WatchlistEntry[];
  isServerHydrated: boolean;
  isSyncing: boolean;
  syncError: string | null;
  addEntry: (entry: WatchlistEntry) => void;
  removeEntry: (featureName: string) => void;
  updateStatus: (featureName: string, status: WatchlistStatus) => void;
  updateNote: (featureName: string, note: string) => void;
  getByStatus: (status: WatchlistStatus) => WatchlistEntry[];
  exportJSON: () => string;
  exportVerifiedJSON: () => string;
  importJSON: (json: string) => void;
  clearAll: () => void;
  hydrateFromServer: () => Promise<void>;
  syncWithServer: () => Promise<void>;
}

let syncTimer: ReturnType<typeof setTimeout> | null = null;

function nowIsoString(): string {
  return new Date().toISOString();
}

function parseDateOrNow(value?: string): string {
  if (!value) {
    return nowIsoString();
  }

  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return nowIsoString();
  }

  return new Date(timestamp).toISOString();
}

function toStatus(value: unknown): WatchlistStatus {
  if (typeof value === 'string' && ALLOWED_STATUSES.includes(value as WatchlistStatus)) {
    return value as WatchlistStatus;
  }
  return 'watching';
}

function normalizeEntry(entry: Partial<WatchlistEntry> & Pick<WatchlistEntry, 'feature_name'>): WatchlistEntry {
  const featureName = entry.feature_name?.trim();
  if (!featureName) {
    throw new Error('feature_name 不可為空');
  }

  return {
    feature_name: featureName,
    task_id: entry.task_id?.trim() || 'unknown',
    status: toStatus(entry.status),
    note: entry.note || '',
    ic_snapshot: typeof entry.ic_snapshot === 'number' && Number.isFinite(entry.ic_snapshot) ? entry.ic_snapshot : null,
    icir_snapshot: typeof entry.icir_snapshot === 'number' && Number.isFinite(entry.icir_snapshot) ? entry.icir_snapshot : null,
    turnover_snapshot:
      typeof entry.turnover_snapshot === 'number' && Number.isFinite(entry.turnover_snapshot)
        ? entry.turnover_snapshot
        : null,
    added_at: parseDateOrNow(entry.added_at),
    updated_at: parseDateOrNow(entry.updated_at),
  };
}

function mergeEntriesByUpdatedAt(entries: WatchlistEntry[]): WatchlistEntry[] {
  const byFeature = new Map<string, WatchlistEntry>();

  for (const entry of entries) {
    const existing = byFeature.get(entry.feature_name);
    if (!existing) {
      byFeature.set(entry.feature_name, entry);
      continue;
    }

    const existingTime = Date.parse(existing.updated_at);
    const incomingTime = Date.parse(entry.updated_at);
    if (Number.isNaN(existingTime) || incomingTime >= existingTime) {
      byFeature.set(entry.feature_name, entry);
    }
  }

  return Array.from(byFeature.values()).sort((left, right) => {
    const leftTs = Date.parse(left.updated_at);
    const rightTs = Date.parse(right.updated_at);
    return (Number.isFinite(rightTs) ? rightTs : 0) - (Number.isFinite(leftTs) ? leftTs : 0);
  });
}

function toExportPayload(entries: WatchlistEntry[]): WatchlistExportPayload {
  return {
    version: '1.0',
    exported_at: nowIsoString(),
    entries,
  };
}

function scheduleServerSync(get: () => WatchlistStoreState): void {
  if (syncTimer) {
    clearTimeout(syncTimer);
  }
  syncTimer = setTimeout(() => {
    void get().syncWithServer();
  }, SERVER_SYNC_DEBOUNCE_MS);
}

export const useWatchlistStore = create<WatchlistStoreState>()(
  persist(
    (set, get) => ({
      entries: [],
      isServerHydrated: false,
      isSyncing: false,
      syncError: null,
      addEntry: (entry) => {
        const state = get();
        const normalized = normalizeEntry({
          ...entry,
          updated_at: nowIsoString(),
          added_at: entry.added_at || nowIsoString(),
        });

        const existing = state.entries.find((item) => item.feature_name === normalized.feature_name);
        if (!existing && state.entries.length >= MAX_WATCHLIST_ENTRIES) {
          throw new Error(`Watchlist 容量已滿（最多 ${MAX_WATCHLIST_ENTRIES} 個因子）`);
        }

        set((current) => {
          const entries = [...current.entries];
          const index = entries.findIndex((item) => item.feature_name === normalized.feature_name);

          if (index === -1) {
            entries.unshift(normalized);
            return { entries };
          }

          const merged: WatchlistEntry = {
            ...entries[index],
            ...normalized,
            added_at: entries[index].added_at || normalized.added_at,
            updated_at: nowIsoString(),
          };
          entries[index] = merged;
          return { entries: mergeEntriesByUpdatedAt(entries) };
        });

        scheduleServerSync(get);
      },
      removeEntry: (featureName) => {
        set((state) => ({ entries: state.entries.filter((item) => item.feature_name !== featureName) }));
        scheduleServerSync(get);
      },
      updateStatus: (featureName, status) => {
        const nextStatus = toStatus(status);
        set((state) => ({
          entries: state.entries.map((item) =>
            item.feature_name === featureName
              ? { ...item, status: nextStatus, updated_at: nowIsoString() }
              : item
          ),
        }));
        scheduleServerSync(get);
      },
      updateNote: (featureName, note) => {
        set((state) => ({
          entries: state.entries.map((item) =>
            item.feature_name === featureName
              ? { ...item, note, updated_at: nowIsoString() }
              : item
          ),
        }));
        scheduleServerSync(get);
      },
      getByStatus: (status) => get().entries.filter((item) => item.status === status),
      exportJSON: () => JSON.stringify(toExportPayload(get().entries), null, 2),
      exportVerifiedJSON: () => {
        const verified = get().entries.filter((item) => item.status === 'verified');
        return JSON.stringify(toExportPayload(verified), null, 2);
      },
      importJSON: (json) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(json);
        } catch {
          throw new Error('JSON 格式錯誤');
        }

        if (!parsed || typeof parsed !== 'object') {
          throw new Error('匯入內容不是有效物件');
        }

        const payload = parsed as Partial<WatchlistExportPayload> & { entries?: unknown[] };
        if (payload.version !== '1.0') {
          throw new Error('不支援的 watchlist version');
        }
        if (!Array.isArray(payload.entries)) {
          throw new Error('entries 欄位格式錯誤');
        }

        const importedEntries = payload.entries
          .map((item) => {
            if (!item || typeof item !== 'object') {
              return null;
            }
            try {
              return normalizeEntry(item as Partial<WatchlistEntry> & Pick<WatchlistEntry, 'feature_name'>);
            } catch {
              return null;
            }
          })
          .filter((item): item is WatchlistEntry => item !== null);

        set((state) => {
          const merged = mergeEntriesByUpdatedAt([...state.entries, ...importedEntries]);
          const trimmed = merged.slice(0, MAX_WATCHLIST_ENTRIES);
          return { entries: trimmed };
        });
        scheduleServerSync(get);
      },
      clearAll: () => {
        set({ entries: [] });
        scheduleServerSync(get);
      },
      hydrateFromServer: async () => {
        if (get().isServerHydrated) {
          return;
        }

        try {
          const response = await fetchWatchlist();
          const remoteEntries = (response.entries || []).map((entry) => normalizeEntry(entry));

          set((state) => {
            const merged = mergeEntriesByUpdatedAt([...state.entries, ...remoteEntries]).slice(
              0,
              MAX_WATCHLIST_ENTRIES
            );
            return {
              entries: merged,
              isServerHydrated: true,
              syncError: null,
            };
          });

          scheduleServerSync(get);
        } catch (error) {
          const message = error instanceof Error ? error.message : '後端同步失敗';
          set({ syncError: message });
        }
      },
      syncWithServer: async () => {
        if (get().isSyncing) {
          return;
        }

        const snapshot = mergeEntriesByUpdatedAt(get().entries).slice(0, MAX_WATCHLIST_ENTRIES);
        set({ isSyncing: true, syncError: null });

        try {
          const response = await syncWatchlist(snapshot);
          const serverEntries = (response.entries || []).map((entry) => normalizeEntry(entry));
          set((state) => ({
            entries: mergeEntriesByUpdatedAt([...state.entries, ...serverEntries]).slice(
              0,
              MAX_WATCHLIST_ENTRIES
            ),
            isServerHydrated: true,
            isSyncing: false,
            syncError: null,
          }));
        } catch (error) {
          const message = error instanceof Error ? error.message : '後端同步失敗';
          set({ isSyncing: false, syncError: message });
        }
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ entries: state.entries }),
    }
  )
);
