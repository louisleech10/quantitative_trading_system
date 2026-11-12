"""共用背景工作紀錄（NOCAP Task 5.3 契約；首個消費端＝ICPERF Task 0.6 (h) ⑦ Coverage 端點改任務制）。

驗收測試：`tests/api/test_nocap_background_jobs.py`、`tests/api/test_icperf_limit_l1c_coverage_tasks.py`。

契約摘要（docs/NOCAP_SPEC.md Task 5.3、docs/ICPERF_SPEC.md Task 0.6 (h) ⑦）：
- 狀態機：`queued → running → {completed, failed, cancelled, interrupted}`；取消請求於 running 時先進
  `cancelling`，於下一個安全點（`ctx.check_cancel()`）生效。終態＝`TERMINAL_STATES`。
- 每次狀態變更、進度推進與結果皆**原子寫入**檔案：先寫同目錄暫存檔再 `os.replace`（以 `os.replace`
  模組屬性呼叫）；紀錄檔 `<root>/<job_id>.json`，結果檔 `<root>/<job_id>.result.json`（先於 completed 紀錄寫入）。
  工作結束後目錄內不殘留暫存檔。
- 紀錄欄位（`get()` 回傳）：`task_id`、`kind`、`params`、`state`、`progress`（`phase`、`processed`、`total`、
  `updated_at`〔ISO 8601〕）、`error`（failed 之錯誤訊息；interrupted 之原因；其餘 None）、`created_at`（ISO 8601）、
  `summary`（工作以 `ctx.set_summary` 寫入之小型摘要；未寫為 None）。
- 進度：`processed` 不減（減少 ⇒ ValueError）；每次推進更新 `updated_at`（嚴格遞增）並原子寫入紀錄檔。
  服務端不依 `updated_at` 自動終止工作。
- 取消為協作式：不強殺執行緒；fn 於安全點呼叫 `ctx.check_cancel()`，已請求取消即拋 `JobCancelled`。
  fn 正常回傳後、提交結果前若已請求取消 ⇒ 晚到結果丟棄、狀態 `cancelled`（不寫結果檔）。
- 啟動時以新實例讀回既有紀錄；`mark_interrupted_on_startup()` 將未終態者（queued／running／cancelling）
  標 `interrupted` 並於 `error` 寫原因。
- 不設任何牆鐘逾時；`wait()` 以 threading.Event 等至終態（無逾時參數）。
- 範圍：單一 API 行程內之執行緒＋本機檔案紀錄（多 worker 行程不共享取消旗標與等待事件；審查 r175 接受之本機範圍）。
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from api.core.logging import get_logger

logger = get_logger(__name__)

#: 終態（不再變更）
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled", "interrupted"})
#: 非終態（啟動時一律標 interrupted）
NON_TERMINAL_STATES = frozenset({"queued", "running", "cancelling"})

_RECORD_SUFFIX = ".json"
_RESULT_SUFFIX = ".result.json"


class JobCancelled(Exception):
    """協作式取消：安全點偵測到取消請求時拋出；fn 拋出本例外 ⇒ 工作狀態 `cancelled`。"""


class JobResultUnavailable(RuntimeError):
    """`read_result` 之工作存在但非 `completed`（queued／running／cancelling／failed／cancelled／interrupted）。"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_default(value: Any) -> Any:
    """numpy 純量／陣列等之 JSON 轉換（結果檔）。"""
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"無法序列化為 JSON：{type(value).__name__}")


class JobContext:
    """傳給工作函式 `fn(ctx)` 之執行情境：回報進度與檢查取消（安全點）。"""

    def __init__(self, store: "BackgroundJobStore", job_id: str) -> None:
        self._store = store
        self._job_id = job_id

    def progress(self, phase: str, processed: int, total: int) -> None:
        """回報進度：`processed` 不得小於前次（否則 ValueError）；更新 `updated_at` 並原子寫入紀錄檔。"""
        self._store._update_progress(self._job_id, str(phase), int(processed), int(total))

    def check_cancel(self) -> None:
        """安全點：已請求取消 ⇒ 拋 `JobCancelled`；否則立即返回。"""
        if self._store._cancel_requested(self._job_id):
            raise JobCancelled(f"工作 {self._job_id} 已請求取消")

    def set_summary(self, summary: Dict[str, Any]) -> None:
        """寫入結果摘要（小型 dict，供狀態查詢顯示；完整結果仍只存結果檔）。"""
        self._store._update_summary(self._job_id, summary)


class BackgroundJobStore:
    """背景工作紀錄庫：每筆工作一個 JSON 紀錄檔（原子寫入），結果另存結果檔。

    Args:
        root_dir: 紀錄目錄（不存在則建立）。
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._terminal_events: Dict[str, threading.Event] = {}

    # ------------------------------------------------------------------ 檔案

    def _record_path(self, job_id: str) -> Path:
        return self.root_dir / f"{job_id}{_RECORD_SUFFIX}"

    def _result_path(self, job_id: str) -> Path:
        return self.root_dir / f"{job_id}{_RESULT_SUFFIX}"

    def _atomic_write(self, path: Path, payload: Any) -> None:
        """同目錄暫存檔寫全 → `os.replace`（原子）；暫存檔名含隨機碼，失敗時清除。"""
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, default=_json_default)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def _read(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self._record_path(job_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _require(self, job_id: str) -> Dict[str, Any]:
        record = self._read(job_id)
        if record is None:
            raise KeyError(job_id)
        return record

    def _write(self, record: Dict[str, Any]) -> None:
        self._atomic_write(self._record_path(record["task_id"]), record)

    def _terminal_event(self, job_id: str) -> threading.Event:
        with self._lock:
            event = self._terminal_events.get(job_id)
            if event is None:
                event = self._terminal_events[job_id] = threading.Event()
            return event

    def _finish(self, record: Dict[str, Any], state: str, error: Optional[str] = None) -> None:
        """轉終態並落盤、喚醒等待者（呼叫端持鎖）。"""
        record["state"] = state
        record["error"] = error
        self._write(record)
        self._terminal_event(record["task_id"]).set()

    # ------------------------------------------------------------------ 公開介面

    def create(self, kind: str, params: Dict[str, Any]) -> str:
        """建立工作紀錄（狀態 `queued`、`created_at` ISO 8601），原子寫入 `<root>/<job_id>.json`，回傳 job_id。"""
        job_id = uuid.uuid4().hex
        created = _now().isoformat()
        record = {
            "task_id": job_id,
            "kind": str(kind),
            "params": params,
            "state": "queued",
            "progress": {"phase": "queued", "processed": 0, "total": 0, "updated_at": created},
            "error": None,
            "created_at": created,
            "summary": None,
        }
        with self._lock:
            self._cancel_flags[job_id] = threading.Event()
            self._terminal_event(job_id)
            self._write(record)
        return job_id

    def start(self, job_id: str, fn: Callable[[JobContext], Any]) -> None:
        """於 daemon 執行緒執行 `fn(ctx)`，狀態轉 `running`（於呼叫 fn 前落盤）。

        - fn 正常回傳：若提交前未請求取消 ⇒ 原子寫入結果檔後狀態 `completed`；若已請求取消 ⇒ 丟棄結果，`cancelled`。
        - fn 拋 `JobCancelled` ⇒ `cancelled`；其他例外 ⇒ `failed`，`error` 為例外訊息。
        """
        with self._lock:
            record = self._require(job_id)
            if record["state"] != "queued":
                raise ValueError(f"工作 {job_id} 狀態為 {record['state']}，僅 queued 可啟動")
            self._cancel_flags.setdefault(job_id, threading.Event())
            record["state"] = "running"
            self._write(record)
        thread = threading.Thread(target=self._run, args=(job_id, fn), name=f"bgjob-{job_id[:8]}", daemon=True)
        thread.start()

    def _run(self, job_id: str, fn: Callable[[JobContext], Any]) -> None:
        ctx = JobContext(self, job_id)
        try:
            result = fn(ctx)
        except JobCancelled:
            with self._lock:
                self._finish(self._require(job_id), "cancelled")
            return
        except Exception as exc:  # noqa: BLE001  # 工作失敗一律落 failed 紀錄（不中斷 API 行程）
            logger.warning("背景工作 %s 失敗：%s", job_id, exc)
            with self._lock:
                self._finish(self._require(job_id), "failed", f"{type(exc).__name__}: {exc}")
            return
        with self._lock:
            record = self._require(job_id)
            if self._cancel_requested(job_id) or record["state"] != "running":
                # 晚到結果不覆寫：已請求取消者丟棄結果；他處已轉終態者（如重啟標 interrupted）不動
                if record["state"] not in TERMINAL_STATES:
                    self._finish(record, "cancelled")
                return
            self._atomic_write(self._result_path(job_id), result)
            self._finish(record, "completed")

    def _cancel_requested(self, job_id: str) -> bool:
        flag = self._cancel_flags.get(job_id)
        return flag is not None and flag.is_set()

    def _update_progress(self, job_id: str, phase: str, processed: int, total: int) -> None:
        with self._lock:
            record = self._require(job_id)
            previous = record.get("progress") or {}
            if processed < int(previous.get("processed", 0)):
                raise ValueError(f"進度不得倒退：{processed} < {previous.get('processed')}")
            now = _now()
            last = previous.get("updated_at")
            if last is not None:
                last_dt = datetime.fromisoformat(last)
                if now <= last_dt:
                    now = last_dt + timedelta(microseconds=1)  # updated_at 嚴格遞增
            record["progress"] = {"phase": phase, "processed": processed, "total": total, "updated_at": now.isoformat()}
            self._write(record)

    def _update_summary(self, job_id: str, summary: Dict[str, Any]) -> None:
        with self._lock:
            record = self._require(job_id)
            record["summary"] = summary
            self._write(record)

    def cancel(self, job_id: str) -> str:
        """請求取消：running ⇒ `"cancelling"`（下一安全點生效）；queued ⇒ `"cancelled"`（立即終態）；
        已終態 ⇒ `"already_terminal"`。未知 job_id ⇒ KeyError。"""
        with self._lock:
            record = self._require(job_id)
            state = record["state"]
            if state in TERMINAL_STATES:
                return "already_terminal"
            self._cancel_flags.setdefault(job_id, threading.Event()).set()
            if state == "queued":
                self._finish(record, "cancelled")
                return "cancelled"
            if state == "running":
                record["state"] = "cancelling"
                self._write(record)
            return "cancelling"

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """回傳紀錄 dict（含 task_id、kind、state、progress、error、created_at）；未知 ⇒ None。
        紀錄可由先前實例寫入同目錄者讀回。"""
        with self._lock:
            return self._read(job_id)

    def read_result(self, job_id: str) -> Any:
        """讀回已完成工作之結果（自結果檔）。未知 ⇒ KeyError；非 completed ⇒ `JobResultUnavailable`。"""
        with self._lock:
            record = self._require(job_id)
            if record["state"] != "completed":
                raise JobResultUnavailable(f"工作 {job_id} 狀態為 {record['state']}，無結果可讀")
            return json.loads(self._result_path(job_id).read_text(encoding="utf-8"))

    def wait(self, job_id: str) -> Dict[str, Any]:
        """阻塞至該工作進入終態（threading.Event，無逾時參數），回傳終態紀錄。未知 ⇒ KeyError。"""
        with self._lock:
            record = self._require(job_id)
            if record["state"] in TERMINAL_STATES:
                return record
            event = self._terminal_event(job_id)
        event.wait()
        return self._require(job_id)

    def mark_interrupted_on_startup(self) -> int:
        """掃描目錄內全部紀錄：未終態者（queued／running／cancelling）標 `interrupted`、`error` 寫原因
        （原子寫入），終態者不動；回傳標記筆數。"""
        marked = 0
        with self._lock:
            for path in sorted(self.root_dir.glob(f"*{_RECORD_SUFFIX}")):
                if path.name.endswith(_RESULT_SUFFIX) or path.name.startswith("."):
                    continue
                record = json.loads(path.read_text(encoding="utf-8"))
                state = record.get("state")
                if state in NON_TERMINAL_STATES:
                    self._finish(record, "interrupted",
                                 f"服務重啟時工作尚未完成（重啟前狀態：{state}），可重新送出")
                    marked += 1
        return marked
