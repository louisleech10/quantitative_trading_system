import type { WatchlistEntry } from '@/lib/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export interface WatchlistQueryResponse {
  version: '1.0';
  updated_at: string;
  entries: WatchlistEntry[];
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const message = error?.detail || error?.message || 'Watchlist API request failed';
    throw new Error(message);
  }

  return response.json();
}

export async function fetchWatchlist(status?: string): Promise<WatchlistQueryResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return request<WatchlistQueryResponse>(`/watchlist${query}`);
}

export async function syncWatchlist(entries: WatchlistEntry[]): Promise<WatchlistQueryResponse> {
  return request<WatchlistQueryResponse>('/watchlist', {
    method: 'PUT',
    body: JSON.stringify({ entries }),
  });
}
