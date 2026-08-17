"""Task 2.3 — 生產者一致性合約（未來搜尋引擎的驗收）。

今日**無真實生產者**（registry G1-R1）；本檔以「假想生產者」呼叫唯一寫入口
`append_trial_attempt`，證明未來引擎接不對即紅——把文件承諾變成可執行合約。
"""

import json
from concurrent.futures import ThreadPoolExecutor

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
