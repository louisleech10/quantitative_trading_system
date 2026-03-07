/// <reference lib="webworker" />

import { parseFeatureNameSegments, type FeatureSegments } from '../lib/featureNameParser';

interface ParseResultItem {
  name: string;
  segments: FeatureSegments;
}

const workerScope = self as unknown as DedicatedWorkerGlobalScope;

workerScope.onmessage = (event: MessageEvent<string[]>) => {
  const names = Array.isArray(event.data) ? event.data : [];
  const result: ParseResultItem[] = names.map((name) => ({
    name,
    segments: parseFeatureNameSegments(name),
  }));

  workerScope.postMessage(result);
};
