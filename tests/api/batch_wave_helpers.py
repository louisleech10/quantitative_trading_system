"""API 批次 wave 測試之共用接縫（ICFIRSTALIGN Task 4.2 遷移；docs/ICFIRSTALIGN_SPEC.md v29）。

改前各檔以 monkeypatch 把 `api.services.feature_factory_batch_service.ProcessPoolExecutor` 換成 `ThreadPoolExecutor`
（避免 pickle 測試 stub 至子行程）。wave 改經預算域排程器後，executor 由 `momentum.factories.create_memory_budget_scheduler`
建立——本 helper 於該 factory 注入 `executor_factory=ThreadPoolExecutor` 與執行緒身分（同 test_icfirstalign_batch_domain），
並以固定任務峰值 E 代替依 kline 形狀之估算（各檔不生成特徵、批次 cache 為暫存目錄，形狀不可得時依 SPEC 會改走串行臂）。
語意不變：同一 wave 之全部項目仍並行執行於行程內執行緒、結果與錯誤分類同改前。
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Tuple

TEST_ENVELOPE_BYTES = 64 << 20


def _thread_identity() -> Tuple[int, float]:
    """行程內執行緒池之任務身分：以執行緒識別代 pid（避免與根同 pid 而被成員去重）。"""
    return (10 ** 9 + threading.get_ident() % 10 ** 6, 0.0)


def use_thread_wave(monkeypatch: Any, executor_factory: Any = ThreadPoolExecutor,
                    envelope: Optional[int] = TEST_ENVELOPE_BYTES, serial: bool = False) -> None:
    """wave 之 executor 改為行程內執行緒池（取代改前之 `ProcessPoolExecutor` 替換）；`executor_factory` 另給者
    （例：建構即失敗之 executor，驗 wave 例外路徑）取代之。`envelope=None` ⇒ 不注入、取正式估算（真實生成之案例：
    行程內執行緒之 worker 讀數即整個測試行程之 footprint，固定小 E 會被判估算低估）。`serial=True` ⇒ 無輔助啟動上界
    （依 SPEC 不准入並行）⇒ 全部項目於根行程之專用執行緒依序呼叫同一 `_compute_single` 本體（真實生成之案例用：
    行程內執行緒並非獨立子行程，其任務峰值 E 之判定無意義）。"""
    from momentum import factories

    real = factories.create_memory_budget_scheduler

    def scheduler(**kw: Any) -> Any:
        kw.setdefault("executor_factory", executor_factory)
        kw.setdefault("task_identity", _thread_identity)
        if serial:
            kw["aux_startup_envelope"] = None
        return real(**kw)

    monkeypatch.setattr(factories, "create_memory_budget_scheduler", scheduler)
    if envelope is not None:
        monkeypatch.setattr(factories, "estimate_symbol_envelope", lambda **kw: envelope)


__all__ = ["TEST_ENVELOPE_BYTES", "use_thread_wave"]
