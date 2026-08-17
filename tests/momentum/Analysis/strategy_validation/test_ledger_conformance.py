"""Task 2.3 — 生產者一致性合約（未來搜尋引擎的驗收）。

今日**無真實生產者**（registry G1-R1）；本檔以「假想生產者」呼叫唯一寫入口
`append_trial_attempt`，證明未來引擎接不對即紅——把文件承諾變成可執行合約。
"""

import enum
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from momentum.Analysis.strategy_validation import ledger as ledger_mod
from momentum.Analysis.strategy_validation.contract import ContractViolation
from momentum.Analysis.strategy_validation.ledger import append_trial_attempt, read_trial_ledger

_SESSION = "conformance-sess"
_DATASET = "conformance-ds"


@pytest.fixture(autouse=True)
def _redirect_ledger_root(tmp_path, monkeypatch):
    def _fake_path(*, research_session_id, dataset_key):
        return tmp_path / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"

    monkeypatch.setattr(ledger_mod, "ledger_path", _fake_path)
    return tmp_path


def _record(idx, *, metric_valid=True, **overrides):
    rec = {
        "research_session_id": _SESSION,
        "dataset_key": _DATASET,
        "candidate_id": f"cand-{idx}",
        "evaluation_id": f"eval-{idx}",
        "attempt_index": 0,
        "state": "complete",
        "metric_name": "sharpe",
        "metric_value": 0.5 + idx * 0.01,
        "metric_unit": "per_period",
        "metric_valid": metric_valid,
        "input_artifact_hash": f"{idx:064d}",
        "ts": "2026-08-18T00:00:00Z",
    }
    rec.update(overrides)
    return rec


def _write(record):
    append_trial_attempt(
        research_session_id=_SESSION, dataset_key=_DATASET, record=record
    )


def _read():
    return read_trial_ledger(research_session_id=_SESSION, dataset_key=_DATASET)


def _path(tmp_path):
    return tmp_path / "strategy_validation" / f"{_SESSION}__{_DATASET}.jsonl"


def test_counts_are_self_consistent_including_invalid_metric():
    """假想生產者寫 N 筆（含 metric_valid=False）⇒ 計數不變式成立且無 rejected 列。"""
    for i in range(9):
        _write(_record(i, metric_valid=(i % 3 != 0)))
    got = _read()
    assert got.n_evaluated == 9
    assert got.n_evaluated == got.n_valid_metrics + got.n_failed_or_pruned
    assert got.n_rows_rejected == 0
    assert got.n_valid_metrics == 6
    assert got.n_failed_or_pruned == 3


@pytest.mark.parametrize(
    "bad",
    [
        {"candidate_id": "x"},                       # 缺鍵
        {**_record(1), "attempt_index": "0"},        # 型別錯
        {**_record(1), "extra_field": True},         # 額外鍵
        {**_record(1), "metric_unit": "weekly"},     # 枚舉外
    ],
)
def test_invalid_record_raises_and_leaves_file_untouched(tmp_path, bad):
    """缺鍵／型別錯 ⇒ raise 且**不寫半列**（行數前後相等）。"""
    _write(_record(0))
    before = _path(tmp_path).read_text(encoding="utf-8").count("\n")
    with pytest.raises(ContractViolation):
        _write(bad)
    after = _path(tmp_path).read_text(encoding="utf-8").count("\n")
    assert before == after == 1


def test_duplicate_evaluation_id_raises():
    """重複 evaluation_id ⇒ raise（append-only 帳本禁重覆記，否則 N 會被灌水）。"""
    _write(_record(1))
    with pytest.raises(ContractViolation, match="evaluation_id"):
        _write(_record(1, candidate_id="cand-other"))


def test_concurrent_appends_do_not_interleave(tmp_path):
    """並發：2 執行緒各 50 筆 ⇒ n_evaluated==100 且每行可 json.loads（無交錯半列）。"""

    def _worker(offset):
        for i in range(50):
            _write(_record(offset + i))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(_worker, [0, 1000]))

    lines = [ln for ln in _path(tmp_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 100
    for line in lines:
        json.loads(line)  # 任一行壞掉即拋
    got = _read()
    assert got.n_evaluated == 100
    assert got.n_rows_rejected == 0


def test_read_after_write_roundtrip_preserves_candidate_set():
    for i in range(4):
        _write(_record(i))
    got = _read()
    assert got.candidate_ids == frozenset({f"cand-{i}" for i in range(4)})
    assert got.n_for_dsr == 4
    assert got.status == "ok"


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_metric_value_is_rejected_at_write(tmp_path, bad_value):
    """A1-21 L1：唯一寫入口拒 NaN／±inf（訊息具名 non_finite），且不寫半列。"""
    _write(_record(0))
    with pytest.raises(ContractViolation, match="non_finite"):
        _write(_record(1, metric_value=bad_value))
    assert _path(tmp_path).read_text(encoding="utf-8").count("\n") == 1
    assert "NaN" not in _path(tmp_path).read_text(encoding="utf-8")


class _StrEnum(str, enum.Enum):
    PER_PERIOD = "per_period"


@pytest.mark.parametrize(
    "field, value, label",
    [
        ("metric_unit", _StrEnum.PER_PERIOD, "Enum 冒充 str"),
        ("metric_value", np.float64(1.2), "numpy.float64 冒充 float"),
        ("attempt_index", np.int64(0), "numpy.int64 冒充 int"),
        ("metric_valid", "true", "字串冒充 bool"),
        ("metric_valid", 1, "int 冒充 bool"),
        ("metric_value", True, "bool 冒充 float"),
    ],
)
def test_exact_type_check_rejects_lookalikes(field, value, label):
    """A1-21 L7：型別精確比對——只收純 Python 純量；Enum／numpy／bool 冒充一律拒（對稱）。"""
    with pytest.raises(ContractViolation, match="bad_type"):
        _write(_record(0, **{field: value}))


def test_error_message_names_missing_and_extra_keys():
    """A1-21 L9：reason 字面單一，但錯誤**訊息**須列出 missing／extra 以利除錯。"""
    bad = {**_record(0), "extra_field": True}
    del bad["ts"]
    with pytest.raises(ContractViolation, match=r"missing=\['ts'\].*extra=\['extra_field'\]"):
        _write(bad)


def test_record_context_must_match_target_ledger(tmp_path):
    """A1-21 L5（codex CROSS_CONTEXT）：record 之 session／dataset 與參數不符 ⇒ 拒寫、檔不建立。"""
    with pytest.raises(ContractViolation, match="不符"):
        append_trial_attempt(
            research_session_id="other-sess", dataset_key=_DATASET, record=_record(0)
        )
    with pytest.raises(ContractViolation, match="不符"):
        append_trial_attempt(
            research_session_id=_SESSION, dataset_key="other-ds", record=_record(0)
        )
    assert not (tmp_path / "strategy_validation").exists()


def test_duplicate_evaluation_id_race_writes_exactly_one_row(tmp_path, monkeypatch):
    """A1-21 L5（TOCTOU，可證偽）：兩執行緒同 evaluation_id、掃描後刻意停 0.3s 放大視窗。

    有 flock：B 在 A 釋放前進不了掃描 ⇒ 掃到重複 ⇒ 恰 1 成功 1 ContractViolation、檔內 1 列。
    拿掉 flock（探針 §V-7e）：兩者皆掃到空檔 ⇒ 皆寫 ⇒ 2 列 ⇒ 本測試轉紅。
    """
    monkeypatch.setattr(ledger_mod, "_after_duplicate_scan_hook", lambda: time.sleep(0.3))
    outcomes = []
    lock = threading.Lock()

    def _worker(tag):
        try:
            _write(_record(7, candidate_id=f"cand-{tag}"))
            with lock:
                outcomes.append("ok")
        except ContractViolation:
            with lock:
                outcomes.append("dup")

    threads = [threading.Thread(target=_worker, args=(t,)) for t in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert sorted(outcomes) == ["dup", "ok"]
    lines = [ln for ln in _path(tmp_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    assert _read().n_evaluated == 1


_REPO_ROOT = Path(__file__).resolve().parents[4]
_CHILD_SCRIPT = r"""
import sys, json
from pathlib import Path
tmp, tag, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
from momentum.Analysis.strategy_validation import ledger as L
L.ledger_path = lambda *, research_session_id, dataset_key: (
    Path(tmp) / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"
)
rec = {
    "research_session_id": "mp-sess", "dataset_key": "mp-ds", "candidate_id": "cand-" + tag,
    "evaluation_id": "eval-" + tag, "attempt_index": 0, "state": "x" * n,
    "metric_name": "sharpe", "metric_value": 0.5, "metric_unit": "per_period",
    "metric_valid": True, "input_artifact_hash": "0" * 64, "ts": "2026-08-18T00:00:00Z",
}
L.append_trial_attempt(research_session_id="mp-sess", dataset_key="mp-ds", record=rec)
print("WROTE", tag)
"""


def test_multi_process_long_lines_do_not_interleave(tmp_path):
    """A1-21 L5（多行程、>PIPE_BUF）：4 個獨立行程各寫一列 8KB（遠大於 PIPE_BUF=512）
    ⇒ 每列可 json.loads、列數恰 4、四個 evaluation_id 齊全（flock 使掃描＋寫入原子）。"""
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", _CHILD_SCRIPT, str(tmp_path), f"p{i}", "8192"],
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for i in range(4)
    ]
    for p in procs:
        out, err = p.communicate(timeout=60)
        assert p.returncode == 0, err
        assert "WROTE" in out
    path = tmp_path / "strategy_validation" / "mp-sess__mp-ds.jsonl"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 4
    ids = {json.loads(ln)["evaluation_id"] for ln in lines}
    assert ids == {f"eval-p{i}" for i in range(4)}


def test_unwritable_directory_raises(tmp_path, monkeypatch):
    """邊界④：磁碟不可寫 ⇒ OSError 上拋（不得靜默吞掉寫入失敗）。"""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)

    def _fake_path(*, research_session_id, dataset_key):
        return blocked / "sub" / f"{research_session_id}__{dataset_key}.jsonl"

    monkeypatch.setattr(ledger_mod, "ledger_path", _fake_path)
    try:
        with pytest.raises(OSError):
            _write(_record(0))
    finally:
        blocked.chmod(0o700)
