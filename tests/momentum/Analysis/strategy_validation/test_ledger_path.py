"""A1-21 L6 — 帳本路徑推導之回歸鎖（三家 R14 確認此前零覆蓋）。

本檔**不** monkeypatch `ledger_path`；改 patch `MomentumConfig.from_project_root` 之 project_root，
使真實推導 `results_path / "strategy_validation" / f"{session}__{dataset}.jsonl"` 被實際執行。
探針 §V-7d（目錄字面改名）須使本檔轉紅。
"""

from pathlib import Path

import pytest

from momentum.Analysis.strategy_validation import ledger as ledger_mod
from momentum.Analysis.strategy_validation.ledger import _ledger_filename, ledger_path
from momentum.core.config import MomentumConfig


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """讓 `MomentumConfig.from_project_root()` 回傳以 tmp_path 為 project_root 之**真實** config。"""
    real = MomentumConfig.from_project_root

    def _patched(cls, project_root=None):
        return real(tmp_path)

    monkeypatch.setattr(MomentumConfig, "from_project_root", classmethod(_patched))
    return tmp_path


def test_ledger_filename_literal():
    assert _ledger_filename(research_session_id="sess", dataset_key="ds") == "sess__ds.jsonl"


def test_ledger_path_derives_from_config_results_path(fake_root):
    got = ledger_path(research_session_id="sess-1", dataset_key="btc-1h")
    assert got == fake_root / "results" / "strategy_validation" / "sess-1__btc-1h.jsonl"
    assert got.parent.name == "strategy_validation"
    assert got.parent.parent == MomentumConfig.from_project_root().results_path
    assert got.name == "sess-1__btc-1h.jsonl"


def test_ledger_path_is_not_patched_in_this_file():
    """守衛：本檔測的是真函式（若有人在此檔加 autouse patch，這裡會抓到）。"""
    assert ledger_mod.ledger_path is ledger_path
    assert "MomentumConfig" in ledger_path.__code__.co_names


@pytest.mark.parametrize(
    "session, dataset",
    [
        ("", "ds"),
        ("sess", ""),
        ("../escape", "ds"),
        ("sess", "a/b"),
        ("sess", ".."),
        ("a__b", "ds"),  # `__` 是檔名內兩識別字之分隔符 ⇒ ("a__b","ds") 與 ("a","b__ds") 會撞檔
        ("sess", "ds\x00"),
    ],
)
def test_ledger_path_rejects_unsafe_identifiers(fake_root, session, dataset):
    """識別字不可作檔名 ⇒ ValueError（fail-loud；禁 path traversal／禁靜默改寫）。"""
    with pytest.raises(ValueError):
        ledger_path(research_session_id=session, dataset_key=dataset)


def test_ledger_path_rejects_non_str(fake_root):
    with pytest.raises(ValueError):
        ledger_path(research_session_id=123, dataset_key="ds")  # type: ignore[arg-type]
