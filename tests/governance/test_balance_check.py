"""NOCAP Task 0.3c／0.4（docs/NOCAP_SPEC.md）：四項平衡比較（scripts/balance_check.py）與 SPEC 範本 §B 必填。

秒級：純函式與範本檢查。施工前為紅（balance_check 為空殼、template_check 未要求 §B）。
"""

from __future__ import annotations

import copy
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("balance_check_under_test", REPO / "scripts" / "balance_check.py")
bc = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bc
_spec.loader.exec_module(bc)  # type: ignore[union-attr]
SCALES = (500, 1000, 2000)
BALANCE_NA = "## §B 四項平衡實測\n- N/A：本票不改計算路徑與使用者操作之耗時（治理與監看）。\n\n"


def _record(seconds: float = 100.0, rss: float = 1e9, diff: float = 0.0, out_bytes: float = 1e6,
            scales: tuple = SCALES) -> Dict[str, Any]:
    pts: List[Dict[str, Any]] = []
    for i, s in enumerate(scales):
        k = (i + 1) / len(scales)  # 成長曲線：各點按規模遞增，末點為比較值
        pts.append({"scale": s, "seconds": seconds * k, "peak_rss_bytes": rss * k,
                    "precision": {"max_abs_diff": diff, "bitwise_equal": diff == 0.0}, "output_bytes": out_bytes * k})
    return {"identity": {"match": {"entrypoint": "scripts/x.py", "hardware": {"cpu": "m", "cores": 8}}}, "points": pts}


def test_boundary_39_time_increase_over_threshold_fails() -> None:
    """耗時增 25%（門檻 20%）⇒ 判變差。"""
    assert bc.compare(_record(), _record(seconds=125.0)) != []


def test_boundary_40_time_increase_within_threshold_passes() -> None:
    """耗時增 10% ⇒ 通過（空串列）。"""
    assert bc.compare(_record(), _record(seconds=110.0)) == []


def test_boundary_41_any_precision_difference_fails() -> None:
    """精度差 1e-12（非零）⇒ 判變差。"""
    assert bc.compare(_record(), _record(diff=1e-12)) != []


def test_boundary_42_output_size_increase_over_threshold_fails() -> None:
    """檔案大小增 15%（門檻 10%）⇒ 判變差。"""
    assert bc.compare(_record(), _record(out_bytes=1.15e6)) != []


def test_boundary_57_peak_rss_increase_over_threshold_fails() -> None:
    """峰值 RSS 增 25%（門檻 20%）⇒ 判變差；增 10% ⇒ 通過。"""
    assert bc.compare(_record(), _record(rss=1.25e9)) != []
    assert bc.compare(_record(), _record(rss=1.10e9)) == []


def test_boundary_43_hardware_mismatch_rejected() -> None:
    """基準與本次硬體不同 ⇒ ValueError（硬體不同不可比）。"""
    other = _record()
    other["identity"]["match"]["hardware"] = {"cpu": "other", "cores": 16}
    with pytest.raises(ValueError):
        bc.compare(_record(), other)


def test_boundary_52_fewer_than_three_points_rejected() -> None:
    """基準或本次少於 3 個規模點（無成長曲線）⇒ ValueError。"""
    with pytest.raises(ValueError):
        bc.compare(_record(scales=(500, 2000)), _record(scales=(500, 2000)))


def test_boundary_53_scale_points_must_align() -> None:
    """基準與本次之規模點不一致 ⇒ ValueError（不同規模不可逐點比）。"""
    with pytest.raises(ValueError):
        bc.compare(_record(), _record(scales=(500, 1000, 4000)))


def _spec_variant(tmp_path: Path, budget_section: str, balance_section: str) -> int:
    src = (REPO / "docs" / "NOCAP_SPEC.md").read_text(encoding="utf-8")
    body = re.sub(r"## §B 驗證運算預算\n.*?(?=## §G)", lambda _m: budget_section + balance_section, src, flags=re.S)
    path = tmp_path / "X_SPEC.md"
    path.write_text(body, encoding="utf-8")
    return subprocess.run(["bash", str(REPO / "scripts" / "template_check.sh"), "spec", str(path)],
                          capture_output=True, text=True).returncode


_BUDGET_SHORT = ("## §B 驗證運算預算\n| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |\n|---|---|---|---|---|---|\n"
                 "| X-BUDGET-1 | 基準凍結 | 路徑甲 | 小規模 | 10 分（收據 a.json） | 無 |\n\n")
_BUDGET_LONG = _BUDGET_SHORT.replace("10 分（收據 a.json）", "3 小時（收據 a.json）")


def test_boundary_44_balance_section_required(tmp_path: Path) -> None:
    """新 SPEC：有 `## §B 四項平衡實測` ⇒ rc=0；缺之 ⇒ rc=1（其餘內容相同）。"""
    assert _spec_variant(tmp_path, _BUDGET_SHORT, BALANCE_NA) == 0
    assert _spec_variant(tmp_path, _BUDGET_SHORT, "") == 1


def test_boundary_54_budget_table_required(tmp_path: Path) -> None:
    """新 SPEC：缺 `## §B 驗證運算預算` 表 ⇒ rc=1。"""
    assert _spec_variant(tmp_path, "", BALANCE_NA) == 1


def test_boundary_55_budget_over_two_hours_requires_saving_plan(tmp_path: Path) -> None:
    """預算表合計逾 2 小時而無「不降驗證之省法」說明 ⇒ rc=1；附省法與小規模驗不到之理由 ⇒ rc=0。"""
    assert _spec_variant(tmp_path, _BUDGET_LONG, BALANCE_NA) == 1
    plan = "- 不降驗證之省法：沿用上次通過之結果（依賴未變）；小規模驗不到之理由：該路徑只在全欄出現。\n\n"
    assert _spec_variant(tmp_path, _BUDGET_LONG + plan, BALANCE_NA) == 0


def test_mutation_huge_threshold_lets_regression_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：耗時門檻放大為 10 倍 ⇒ 耗時增 25% 不再判變差（boundary 39 之鑑別力）。"""
    loose = copy.deepcopy(bc.DEFAULT_THRESHOLDS)
    loose["seconds_increase"] = 10.0
    monkeypatch.setattr(bc, "DEFAULT_THRESHOLDS", loose)
    assert bc.compare(_record(), _record(seconds=125.0)) == []
