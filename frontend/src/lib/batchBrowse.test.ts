import { describe, expect, it } from 'vitest';

import { getBackendBrowseTaskId } from './batchBrowse';

describe('getBackendBrowseTaskId', () => {
  it('returns the backend browse id when present', () => {
    expect(
      getBackendBrowseTaskId(
        { browse_task_ids: { BTCUSDT: 'browse_BTCUSDT_1h' } },
        'BTCUSDT',
      ),
    ).toBe('browse_BTCUSDT_1h');
  });

  it('returns null for old batch payloads without browse ids', () => {
    expect(getBackendBrowseTaskId({}, 'BTCUSDT')).toBeNull();
  });
});
