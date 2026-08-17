"""Task 2.2 驗證：N 帳本讀取（計數語意 A1-7、fail-closed、snapshot、candidate_ids）。

mutation §V-7（缺檔時回 n=1）須使本檔轉紅。
"""

import json

import pytest

from momentum.Analysis.strategy_validation import ledger as ledger_mod
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult, read_trial_ledger

_SESSION = "sess-20260818"
_DATASET = "ds-1h"


@pytest.fixture(autouse=True)
def _redirect_ledger_root(tmp_path, monkeypatch):
    """把帳本根目錄導到 tmp_path（不碰真實 results/）。"""

    def _fake_path(*, research_session_id, dataset_key):
        return tmp_path / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"

    monkeypatch.setattr(ledger_mod, "ledger_path", _fake_path)
    return tmp_path


def _row(**overrides):
    row = {
        "research_session_id": _SESSION,
        "dataset_key": _DATASET,
        "candidate_id": "cand-1",
        "evaluation_id": "eval-1",
        "attempt_index": 0,
        "state": "complete",
        "metric_name": "sharpe",
        "metric_value": 1.25,
        "metric_unit": "per_period",
        "metric_valid": True,
        "input_artifact_hash": "a" * 64,
        "ts": "2026-08-18T00:00:00Z",
    }
    row.update(overrides)
    return row


def _write(tmp_path, rows):
    path = tmp_path / "strategy_validation" / f"{_SESSION}__{_DATASET}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write((row if isinstance(row, str) else json.dumps(row)) + "\n")
    return path


def _read():
    return read_trial_ledger(research_session_id=_SESSION, dataset_key=_DATASET)


def test_missing_file_is_n_unknown():
    """① 無檔 ⇒ status 非 ok 且 reason==n_unknown（§V-7 mutation 鎖：回 n=1 即轉紅）。"""
    got = _read()
    assert isinstance(got, LedgerReadResult)
    assert got.status != "ok"
    assert got.reason == "n_unknown"
    assert got.n_candidates_considered == 0
    assert got.n_for_dsr == 0


def test_empty_file_is_n_unknown(_redirect_ledger_root):
    _write(_redirect_ledger_root, [])
    got = _read()
    assert got.status != "ok"
    assert got.reason == "n_unknown"


def test_schema_invalid_row_counts_into_rows_rejected(_redirect_ledger_root):
    """② 3 合法＋1 schema-invalid ⇒ n_evaluated==3、n_rows_rejected==1、n_failed_or_pruned==0。"""
    rows = [
        _row(candidate_id="c1", evaluation_id="e1"),
        _row(candidate_id="c2", evaluation_id="e2"),
        _row(candidate_id="c3", evaluation_id="e3"),
        "{not json",
    ]
    _write(_redirect_ledger_root, rows)
    got = _read()
    assert got.n_evaluated == 3
    assert got.n_rows_rejected == 1
    assert got.n_failed_or_pruned == 0
    assert got.reason == "ledger_row_invalid"


def test_metric_invalid_row_counts_into_failed_and_invariant_holds(_redirect_ledger_root):
    """②b 4 合法其中 1 列 metric_valid=False ⇒ 不變式成立且 rows_rejected==0。"""
    rows = [
        _row(candidate_id="c1", evaluation_id="e1"),
        _row(candidate_id="c2", evaluation_id="e2"),
        _row(candidate_id="c3", evaluation_id="e3"),
        _row(candidate_id="c4", evaluation_id="e4", metric_valid=False),
    ]
    _write(_redirect_ledger_root, rows)
    got = _read()
    assert got.n_evaluated == 4
    assert got.n_valid_metrics == 3
    assert got.n_failed_or_pruned == 1
    assert got.n_rows_rejected == 0
    assert got.n_evaluated == got.n_valid_metrics + got.n_failed_or_pruned


@pytest.mark.parametrize("n_rows", [1, 3, 5])
def test_n_is_lower_bound_always_true(_redirect_ledger_root, n_rows):
    """③ n_is_lower_bound 恆 True（三種輸入）。"""
    _write(
        _redirect_ledger_root,
        [_row(candidate_id=f"c{i}", evaluation_id=f"e{i}") for i in range(n_rows)],
    )
    assert _read().n_is_lower_bound is True


def test_valid_sharpe_values_only_per_period(_redirect_ledger_root):
    """④⑥b 只收 sharpe∧per_period∧valid；annualized row 屬 schema-valid 但不入序列。"""
    rows = [
        _row(candidate_id="c1", evaluation_id="e1", metric_value=1.1),
        _row(candidate_id="c2", evaluation_id="e2", metric_value=2.2),
        _row(candidate_id="c3", evaluation_id="e3", metric_unit="annualized", metric_value=9.9),
        _row(candidate_id="c4", evaluation_id="e4", metric_name="mean_return", metric_value=0.3),
        _row(candidate_id="c5", evaluation_id="e5", metric_valid=False, metric_value=3.3),
    ]
    _write(_redirect_ledger_root, rows)
    got = _read()
    assert got.valid_sharpe_values == (1.1, 2.2)
    # A1-21 L3（取代 TODO ⑥b「計入 n_rows_rejected」字面）：annualized 是合法枚舉 ⇒ schema-valid，
    # 計入 n_evaluated、n_rows_rejected 不增、reason 為空（把「不是 rejected」鎖成可證偽）。
    assert got.n_rows_rejected == 0
    assert got.n_evaluated == 5
    assert got.n_valid_metrics == 4
    assert got.n_failed_or_pruned == 1
    assert got.reason == ""
    assert got.status == "ok"


def test_same_candidate_multiple_attempts(_redirect_ledger_root):
    """⑤⑥c 同 candidate 兩 attempt ⇒ considered==1、evaluated==2、candidate_ids 長度不變式。"""
    rows = [
        _row(candidate_id="c1", evaluation_id="e1", attempt_index=0),
        _row(candidate_id="c1", evaluation_id="e2", attempt_index=1),
    ]
    _write(_redirect_ledger_root, rows)
    got = _read()
    assert got.n_candidates_considered == 1
    assert got.n_evaluated == 2
    assert got.n_for_dsr == got.n_candidates_considered
    assert len(got.candidate_ids) == got.n_candidates_considered
    assert got.candidate_ids == frozenset({"c1"})


def test_snapshot_hash_stable_and_changes_with_new_row(_redirect_ledger_root):
    """⑦ 同一組 row 重讀同值；多一列（新 artifact hash）⇒ 變值。"""
    rows = [_row(candidate_id="c1", evaluation_id="e1", input_artifact_hash="a" * 64)]
    _write(_redirect_ledger_root, rows)
    first = _read().snapshot_hash
    assert first == _read().snapshot_hash
    rows.append(_row(candidate_id="c2", evaluation_id="e2", input_artifact_hash="b" * 64))
    _write(_redirect_ledger_root, rows)
    assert _read().snapshot_hash != first


@pytest.mark.parametrize(
    "bad_row",
    [
        {"candidate_id": "c1"},  # 缺鍵
        _row(attempt_index="0"),  # 型別錯
        {**_row(), "extra": 1},  # 額外鍵
        _row(metric_unit="daily"),  # metric_unit 非枚舉
        _row(metric_valid=1),  # bool 欄位給 int
    ],
)
def test_invalid_rows_rejected_with_named_reason(_redirect_ledger_root, bad_row):
    """⑧ 各類非法 row ⇒ 計入 n_rows_rejected 且 reason 為契約字面。"""
    _write(_redirect_ledger_root, [bad_row])
    got = _read()
    assert got.n_rows_rejected == 1
    assert got.n_evaluated == 0
    assert "ledger_row_invalid" in got.reasons_seen
    # A1-21 L2：檔存在但全列非法 ⇒ 是「帳本損壞」不是「無帳本」：reason 為 ledger_row_invalid、
    # status 仍 unavailable（fail-closed，N=0）；n_unknown 只留給檔缺／真·零列。
    assert got.reason == "ledger_row_invalid"
    assert got.status == "unavailable"
    assert got.n_for_dsr == 0


@pytest.mark.parametrize("bad_value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_metric_value_is_schema_invalid(_redirect_ledger_root, bad_value):
    """A1-21 L1：metric_value 為 NaN／±inf ⇒ schema-invalid（計 n_rows_rejected），
    **不**進 valid_sharpe_values（否則 B3 DSR 之 variance 會被投毒）。"""
    good = _row(candidate_id="c1", evaluation_id="e1", metric_value=1.5)
    bad_line = json.dumps(_row(candidate_id="c2", evaluation_id="e2")).replace(
        "1.25", bad_value
    )
    assert bad_value in bad_line  # 手植（json.dumps 預設 allow_nan 會寫出這些字面）
    _write(_redirect_ledger_root, [good, bad_line])
    got = _read()
    assert got.n_evaluated == 1
    assert got.n_rows_rejected == 1
    assert got.valid_sharpe_values == (1.5,)
    assert got.reason == "ledger_row_invalid"


def test_row_with_foreign_context_is_rejected(_redirect_ledger_root):
    """A1-21 L5：row 之 research_session_id／dataset_key 與本帳本不符 ⇒ 對本帳本非法（不計入 N）。"""
    rows = [
        _row(candidate_id="c1", evaluation_id="e1"),
        _row(candidate_id="c2", evaluation_id="e2", research_session_id="someone-else"),
        _row(candidate_id="c3", evaluation_id="e3", dataset_key="other-ds"),
    ]
    _write(_redirect_ledger_root, rows)
    got = _read()
    assert got.n_evaluated == 1
    assert got.n_rows_rejected == 2
    assert got.candidate_ids == frozenset({"c1"})


@pytest.mark.parametrize(
    "left, right",
    [
        # 三家 R14 反例：舊法 ",".join(hashes)+"|"+dataset+"|"+session 對這三組皆同 payload
        ((["h1"], "a|b", "c"), (["h1"], "a", "b|c")),
        ((["x"], "a|b", "c"), (["x|a"], "b", "c")),
        ((["a"], "b|c", "d"), (["a"], "b", "c|d")),
        ((["h1", "h2"], "d", "s"), (["h1,h2"], "d", "s")),
    ],
)
def test_snapshot_hash_has_no_delimiter_collision(left, right):
    """A1-21 L4：分量含 `|`／`,` 時不同輸入不得同 hash（JSON 定界，非裸拼接）。"""
    assert ledger_mod._snapshot_hash(*left) != ledger_mod._snapshot_hash(*right)


def test_snapshot_hash_at_read_level_distinguishes_delimiter_inputs(_redirect_ledger_root, monkeypatch):
    """讀路徑層級：dataset_key 含 `|` 的兩個不同帳本，snapshot_hash 不同。"""

    def _fake_path(*, research_session_id, dataset_key):
        safe = dataset_key.replace("|", "%7C")
        return _redirect_ledger_root / "strategy_validation" / f"{research_session_id}__{safe}.jsonl"

    monkeypatch.setattr(ledger_mod, "ledger_path", _fake_path)
    hashes = []
    for session, dataset in (("c", "a|b"), ("b|c", "a")):
        path = _fake_path(research_session_id=session, dataset_key=dataset)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(_row(research_session_id=session, dataset_key=dataset)) + "\n",
            encoding="utf-8",
        )
        got = read_trial_ledger(research_session_id=session, dataset_key=dataset)
        assert got.status == "ok"
        hashes.append(got.snapshot_hash)
    assert hashes[0] != hashes[1]


def test_unreadable_file_raises_rather_than_silently_ok(_redirect_ledger_root):
    """邊界⑥：檔案不可讀 ⇒ OSError 上拋（不得靜默當成 n_unknown）。"""
    path = _write(_redirect_ledger_root, [_row()])
    path.chmod(0o000)
    try:
        with pytest.raises(OSError):
            _read()
    finally:
        path.chmod(0o644)
