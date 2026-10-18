/**
 * FF-NAME Task 3.3 — 欄名描述 hook（顯示或篩選特徵欄名之元件一律經此查共享 map）。
 */
import { useCallback, useMemo } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import type { ResolvedFeatureDescriptor } from '@/lib/types';
import {
  buildFeatureDescriptorMap,
  resolveFeatureDescriptor,
  type FeatureDescriptorMap,
  type FeatureDescriptorSourceRow,
} from '@/lib/featureDescriptorMap';

export { buildFeatureDescriptorMap, resolveFeatureDescriptor };
export type { FeatureDescriptorMap, FeatureDescriptorSourceRow };

const EMPTY_MAP: FeatureDescriptorMap = new Map();

export interface UseFeatureDescriptorResult {
  map: FeatureDescriptorMap;
  /** 查描述；查無即 unsupported。 */
  resolve: (name: string) => ResolvedFeatureDescriptor;
  /** 把 API 回傳列之描述併入該 task 的共享 map。 */
  ingest: (rows: ReadonlyArray<FeatureDescriptorSourceRow>) => void;
}

export function useFeatureDescriptor(taskId: string): UseFeatureDescriptorResult {
  const map = useFeatureFactoryStore((state) => state.featureDescriptorMapByTask[taskId]) ?? EMPTY_MAP;
  const mergeDescriptors = useFeatureFactoryStore((state) => state.mergeFeatureDescriptorsForTask);
  const resolve = useCallback((name: string) => resolveFeatureDescriptor(map, name), [map]);
  const ingest = useCallback(
    (rows: ReadonlyArray<FeatureDescriptorSourceRow>) => mergeDescriptors(taskId, rows),
    [mergeDescriptors, taskId],
  );
  return useMemo(() => ({ map, resolve, ingest }), [map, resolve, ingest]);
}
