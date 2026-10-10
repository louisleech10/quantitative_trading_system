"""TESTREG 記錄器（docs/TESTREG_SPEC.md Task 1.3）：每次 pytest session 自動寫 ledger 與增量 summary。

契約：tests/registry/testreg_schema.json 之 `ledger`（session_record／test_record／collect_record／outcome_aggregation／
nested_rule／env_prefixes／argv_norm_drop_dests）與 `summary`。資料位置一律相對 pytest `config.rootpath`
（ledger＝`ledger.dir`、summary＝`summary.path`／`summary.lock`、kline＝`KLINE_REL`、雜湊快取＝`KLINE_CACHE_REL`）；
schema 讀本檔所在 repo 之單一真相源。

TODO 凍結之介面（docs/manifests/TESTREG.json）：本檔目前只含簽章；函式體一律 `raise NotImplementedError`，於第 1 批
實作，並由 Task 1.3 於 `tests/conftest.py` 之 `pytest_plugins` 掛載（現未掛載，不影響任何 session）。

行為約束（SPEC §C）：不改 outcome、執行順序、rc；除 `.testreg/` 外不新增、不改任何檔；記錄器自身之例外一律經
`safe` 攔截並以單行 stderr 告知、不上拋；巢狀 session（環境變數 `TESTREG_PARENT_SESSION` 存在）不寫任何 ledger 檔；
不在每條測試後寫檔（`pytest_sessionfinish` 一次原子寫）。

具名縫（hook 於呼叫當下以模組屬性取用，供 tests/registry/test_testreg_recorder.py 之 mutation 置換）：
`safe`、`is_nested`、`argv_norm`、`sha256_file`、`kline_cache_key`、`kline_sha256`、`aggregate_outcome`、
`write_ledger`、`read_summary`、`summary_lock`、`merge_summary`。

暫存檔命名：`<ledger.dir>/<session_id>.jsonl.tmp-<pid>`（暫存檔＋rename 原子寫）；session 開始時清除 pid 已不存在之
`*.tmp-<pid>`（不清他行程仍存活者，供並行 session）。

kline 雜湊快取檔格式（單一條目）：`{"key": [dev, inode, size, mtime_ns, ctime_ns], "sha256": "<64 hex>"}`。
"""
from __future__ import annotations

import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

PARENT_ENV = "TESTREG_PARENT_SESSION"
KLINE_REL = "data_cache/feature_klines/kline_cache.h5"
KLINE_CACHE_REL = ".testreg/kline_sha_cache.json"
KLINE_CACHE_LOCK_REL = ".testreg/kline_sha_cache.lock"
TMP_INFIX = ".jsonl.tmp-"


def safe(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """呼叫 fn；任何例外攔截後以單行 stderr（前綴 `testreg-recorder:`）告知並回傳 None，不上拋。"""
    raise NotImplementedError("TESTREG Task 1.3")


def is_nested(environ: Mapping[str, str] = os.environ) -> bool:
    """schema `ledger.nested_rule`：環境變數 TESTREG_PARENT_SESSION 存在 ⇒ True。"""
    raise NotImplementedError("TESTREG Task 1.3")


def argv_norm(config: Any) -> str:
    """schema `ledger.session_record.argv_norm`：config.option 全部 dest＝value 去除 `argv_norm_drop_dests`，連同
    config.args（保序）序列化為正規 JSON（sort_keys、無空白）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def sha256_file(path: Path) -> str:
    """全檔 sha256（hex）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def kline_cache_key(st: os.stat_result) -> Tuple[int, int, int, int, int]:
    """快取鍵＝(dev, inode, size, mtime_ns, ctime_ns)。"""
    raise NotImplementedError("TESTREG Task 1.3")


def kline_sha256(rootpath: Path) -> str:
    """schema `ledger.session_record.kline_sha256`：stat→`sha256_file`→stat，兩次鍵不同重試一次，仍不同 ⇒ 字面
    unstable（不寫快取）；檔不存在 ⇒ 字面 absent；快取於獨占鎖內以暫存檔＋rename 原子替換、毀損視同不存在。"""
    raise NotImplementedError("TESTREG Task 1.3")


def session_record(config: Any, session_id: str) -> Dict[str, Any]:
    """依 `ledger.session_record` 計算全部欄位（含 fingerprint 與 duration_class 公式；unstable 時 U＝session_id）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def aggregate_outcome(reports: Mapping[str, Any]) -> Tuple[str, str, bool]:
    """schema `ledger.outcome_aggregation`：{"setup"|"call"|"teardown": TestReport} → (outcome, phase_failed,
    teardown_failed)。"""
    raise NotImplementedError("TESTREG Task 1.3")


def test_record(session_id: str, nodeid: str, order: int, reports: Mapping[str, Any],
                rootpath: Path) -> Dict[str, Any]:
    """依 `ledger.test_record` 由三階段報告組一筆（exception_* 、fail_line、fail_frames、markers）。"""
    raise NotImplementedError("TESTREG Task 1.3")


test_record.__test__ = False  # 名稱以 test_ 開頭，防 pytest 誤收集


def write_ledger(ledger_dir: Path, session_id: str, records: Iterable[Mapping[str, Any]]) -> Path:
    """一次原子寫 `<session_id>.jsonl`（暫存檔＋rename）；回傳最終路徑。"""
    raise NotImplementedError("TESTREG Task 1.3")


def read_summary(path: Path, schema: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """讀 summary；JSON 無法解析、schema_version／k 不符或形狀不符 schema `summary.shape` ⇒ None（視同不存在）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def summary_lock(lock_path: Path) -> AbstractContextManager:
    """fcntl.flock 獨占鎖之 context manager。"""
    raise NotImplementedError("TESTREG Task 1.3")


def merge_summary(rootpath: Path, schema: Mapping[str, Any], records: List[Mapping[str, Any]],
                  session: Mapping[str, Any]) -> None:
    """於 `summary_lock` 內「讀（`read_summary`）→合併（每 nodeid 依 started 保留最近 k 筆）→暫存檔→rename」；
    讀回 None ⇒ 由 ledger 全量重建（同鎖內）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def pytest_sessionstart(session: Any) -> None:
    """計算 session_record、清除過期暫存檔、設 TESTREG_PARENT_SESSION（巢狀 session 不寫）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def pytest_runtest_logreport(report: Any) -> None:
    """累積 setup／call／teardown 報告為一筆 test_record（不寫檔）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def pytest_collectreport(report: Any) -> None:
    """outcome=failed 之收集報告記為 collect_record（不寫檔）。"""
    raise NotImplementedError("TESTREG Task 1.3")


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """一次原子寫本 session 之 jsonl，並合併 summary。"""
    raise NotImplementedError("TESTREG Task 1.3")
