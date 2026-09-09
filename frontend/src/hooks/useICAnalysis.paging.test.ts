/**
 * ICRESULT_PAGING Task 2.1（docs/ICRESULT_PAGING_SPEC.md §C-7／§C-10）：
 * light 回應 setReport／view 不符 ⇒ setError 不吃全量／summary 409 重拉一次／abort 舊 detail 請求／
 * refilter 重置 offset＋abort＋revision 更新／舊世代回應丟棄。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useICAnalysisStore } from '@/store/icAnalysisStore';

type Resp = { ok: boolean; status: number; json: () => Promise<unknown> };
const ok = (body: unknown): Resp => ({ ok: true, status: 200, json: async () => body });
const err = (status: number, body: unknown): Resp => ({ ok: false, status, json: async () => body });

const light = (revision: number, rows = [{ feature_name: 'f1', rank: 1, ic_mean: 0.1, icir: 0.5 }]) => ({
  view: 'light',
  total_features: rows.length,
  result_revision: revision,
  summary_page: { total: rows.length, offset: 0, limit: 50, sort_by: 'icir', sort_order: 'desc', result_revision: revision, rows },
  filter_log_funnel: { stage0_ingestion: { input: 10, output: null } },
  metadata: {},
  analysis_status: 'ok_oos',
});

describe('useICAnalysis — ICRESULT_PAGING', () => {
  beforeEach(() => {
    useICAnalysisStore.getState().resetReport();
    useICAnalysisStore.setState({ taskId: 't1', status: 'completed', error: null });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('fetchResult 打 ?view=light 並 setReport；resultRevision／summaryPage 由回應而來', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(light(3)));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => { await result.current.fetchResult('t1'); });
    expect(String(fetchMock.mock.calls[0][0])).toContain('/result/t1?view=light');
    const st = useICAnalysisStore.getState();
    expect((st.report as { view?: string })?.view).toBe('light');
    expect(st.resultRevision).toBe(3);
    expect(st.summaryPage?.rows[0].feature_name).toBe('f1');
  });

  it('後端舊版（回應無 view:light）⇒ setError、不 setReport（不吃全量）', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ summary_table: new Array(5).fill({ feature_name: 'x' }) })));
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => { await result.current.fetchResult('t1'); });
    const st = useICAnalysisStore.getState();
    expect(st.report).toBeNull();
    expect(st.error).toContain('後端版本過舊');
  });

  it('summary 409 ⇒ 以 current_revision 重拉一次（第二次帶新 revision）', async () => {
    useICAnalysisStore.setState({ resultRevision: 1 });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(err(409, { detail: { message: 'stale', current_revision: 2 } }))
      .mockResolvedValueOnce(ok({ total: 1, offset: 0, limit: 50, sort_by: 'icir', sort_order: 'desc', result_revision: 2, rows: [{ feature_name: 'f2' }] }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.fetchSummaryPage('t1', { sort_by: 'icir', sort_order: 'desc', offset: 0, limit: 50 });
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[0][0])).toContain('revision=1');
    expect(String(fetchMock.mock.calls[1][0])).toContain('revision=2');
    expect(useICAnalysisStore.getState().resultRevision).toBe(2);
    expect(useICAnalysisStore.getState().summaryPage?.rows[0].feature_name).toBe('f2');
  });

  it('summary 參數以 sort_by／sort_order／search 命名（對齊 Feature Factory）', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ total: 0, offset: 0, limit: 50, sort_by: 'ic_mean', sort_order: 'asc', result_revision: null, rows: [] }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.fetchSummaryPage('t1', { sort_by: 'ic_mean', sort_order: 'asc', offset: 50, limit: 50, search: 'close' });
    });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('sort_by=ic_mean');
    expect(url).toContain('sort_order=asc');
    expect(url).toContain('search=close');
    expect(url).toContain('offset=50');
    expect(url).not.toContain('&order=');
    expect(url).not.toContain('&q=');
  });

  it('舊世代 summary 回應（result_revision ≠ store）⇒ 丟棄', async () => {
    useICAnalysisStore.setState({ resultRevision: 5 });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ total: 1, offset: 0, limit: 50, sort_by: 'icir', sort_order: 'desc', result_revision: 4, rows: [{ feature_name: 'stale' }] })));
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => {
      await result.current.fetchSummaryPage('t1', { sort_by: 'icir', sort_order: 'desc', offset: 0, limit: 50 });
    });
    expect(useICAnalysisStore.getState().summaryPage).toBeNull();
  });

  it('切換特徵：前一 detail 請求被 abort；切換中 featureDetail 保留舊值（status=loading）', async () => {
    vi.useFakeTimers();
    useICAnalysisStore.setState({ resultRevision: 1 });
    useICAnalysisStore.getState().setFeatureDetail({ feature_name: 'old', summary_row: { feature_name: 'old' } as never, result_revision: 1 }, 'ready');
    const seen: AbortSignal[] = [];
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      seen.push(init!.signal as AbortSignal);
      return new Promise((resolve) => setTimeout(() => resolve(ok({ feature_name: 'new', summary_row: { feature_name: 'new' }, result_revision: 1 })), 1000));
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { void result.current.fetchFeatureDetail('t1', 'a'); });
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });
    expect(useICAnalysisStore.getState().featureDetailStatus).toBe('loading');
    expect(useICAnalysisStore.getState().featureDetail?.feature_name).toBe('old');
    act(() => { void result.current.fetchFeatureDetail('t1', 'b'); });
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(seen[0].aborted).toBe(true);
    expect(useICAnalysisStore.getState().featureDetail?.feature_name).toBe('new');
    expect(useICAnalysisStore.getState().featureDetailStatus).toBe('ready');
  });

  it('refilter 打 ?view=light、更新 revision、offset 歸 0、abort 進行中投影', async () => {
    useICAnalysisStore.getState().setSummaryParams({ offset: 100 });
    useICAnalysisStore.setState({ resultRevision: 1 });
    let abortedSignal: AbortSignal | null = null;
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (String(url).includes('/summary')) {
        abortedSignal = init!.signal as AbortSignal;
        return new Promise(() => undefined); // 永不回：等被 abort
      }
      return Promise.resolve(ok(light(2)));
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { void result.current.fetchSummaryPage('t1', { sort_by: 'icir', sort_order: 'desc', offset: 100, limit: 50 }); });
    await act(async () => {
      await result.current.refilter('t1', { ic_mean_min: 0, icir_min: 0, p_value_max: 1, correlation_threshold: 0.7 } as never);
    });
    const url = String(fetchMock.mock.calls.find((c) => String(c[0]).includes('/refilter'))?.[0]);
    expect(url).toContain('view=light');
    expect(abortedSignal!.aborted).toBe(true);
    expect(useICAnalysisStore.getState().resultRevision).toBe(2);
    expect(useICAnalysisStore.getState().summaryParams.offset).toBe(0);
  });
});

describe('useICAnalysis — B2 review R1 閉合', () => {
  beforeEach(() => {
    useICAnalysisStore.getState().resetReport();
    useICAnalysisStore.setState({ taskId: 't1', status: 'completed', error: null });
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

  it('refilter 回應無 view:light（舊後端全量）⇒ setError、不 setReport、舊 report 保留', async () => {
    useICAnalysisStore.getState().setReport(light(1) as never);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ summary_table: new Array(39000).fill({ feature_name: 'x' }) })));
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => { await result.current.refilter('t1', { ic_mean_min: 0, icir_min: 0, p_value_max: 1, correlation_threshold: 0.7 } as never); });
    const st = useICAnalysisStore.getState();
    expect((st.report as { view?: string })?.view).toBe('light');
    expect((st.report as { summary_table?: unknown[] })?.summary_table).toBeUndefined();
    expect(st.error).toContain('後端版本過舊');
  });

  it('feature detail 409 ⇒ 以 current_revision 重拉一次；第二次 409 ⇒ error', async () => {
    vi.useFakeTimers();
    useICAnalysisStore.setState({ resultRevision: 1 });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(err(409, { detail: { message: 'stale', current_revision: 2 } }))
      .mockResolvedValueOnce(ok({ feature_name: 'a', summary_row: { feature_name: 'a' }, result_revision: 2 }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useICAnalysis());
    act(() => { void result.current.fetchFeatureDetail('t1', 'a'); });
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1][0])).toContain('revision=2');
    expect(useICAnalysisStore.getState().featureDetailStatus).toBe('ready');
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(err(409, { detail: { message: 'stale', current_revision: 3 } }));
    act(() => { void result.current.fetchFeatureDetail('t1', 'b'); });
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(useICAnalysisStore.getState().featureDetailStatus).toBe('error');
  });

  it('revision 嚴格比較：store=5、回應 result_revision=null ⇒ summary／detail 皆丟棄', async () => {
    vi.useFakeTimers();
    useICAnalysisStore.setState({ resultRevision: 5 });
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(
      String(url).includes('/summary')
        ? ok({ total: 1, offset: 0, limit: 50, sort_by: 'icir', sort_order: 'desc', result_revision: null, rows: [{ feature_name: 'stale' }] })
        : ok({ feature_name: 'stale', summary_row: { feature_name: 'stale' }, result_revision: null })
    )));
    const { result } = renderHook(() => useICAnalysis());
    await act(async () => { await result.current.fetchSummaryPage('t1', { sort_by: 'icir', sort_order: 'desc', offset: 0, limit: 50 }); });
    expect(useICAnalysisStore.getState().summaryPage).toBeNull();
    expect(useICAnalysisStore.getState().summaryError).toContain('result_revision');
    act(() => { void result.current.fetchFeatureDetail('t1', 'stale'); });
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(useICAnalysisStore.getState().featureDetail).toBeNull();
  });
});
