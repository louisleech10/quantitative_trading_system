"""GAP-3 UX Task 6.0 驗收（`-k ic_feature_cap`）——IC 錯誤 reason 之登記處。

邊界①：契約 `reasons` 含 `analysis_rejected` 分類且其中有 `feature_count_exceeds_cap`，`len(r) == 4`。
邊界②：`api/` 與 `frontend/src/` 內該字面之硬編碼數 `== 0`（一律由契約取字面）。

🔴 斷言一律用**成員資格**（`in`）而非等值——Task 7.7 會往**同一個** `analysis_rejected`
再加兩個 reason，寫成 `== ['feature_count_exceeds_cap']` 會在 7.7 上線時假紅。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from momentum.factories import ic_report_reason, ic_report_reasons

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "ic_report_contract.json"


def test_gap3_ic_feature_cap_reason_registered_in_ic_side_contract():
    """邊界①：SPEC L2114 之一行斷言，逐字同形。"""
    c = json.loads(CONTRACT.read_text(encoding="utf-8"))
    r = c["reasons"]
    assert "analysis_rejected" in r
    assert "feature_count_exceeds_cap" in r["analysis_rejected"]
    assert len(r) == 4
    # 🔴 這是**匯入**契約以外的檔：reason 不屬 event_import_contract（那是匯入契約）
    assert not (REPO / "momentum" / "Analysis" / "contracts" / "event_import_contract.json").read_text(
        encoding="utf-8").count("feature_count_exceeds_cap")


def test_gap3_ic_feature_cap_reason_membership_not_equality():
    """🔴 消費端須以成員資格取用；本條同時釘住「清單可擴充」這個設計意圖。

    Task 7.7 會往同一分類再加 reason ⇒ 任何寫等值的消費端都會在那時假紅。
    """
    reasons = ic_report_reasons("analysis_rejected")
    assert "feature_count_exceeds_cap" in reasons          # 成員資格
    assert isinstance(reasons, tuple) and len(reasons) >= 1
    assert ic_report_reason("analysis_rejected") == reasons[0]


def test_gap3_ic_feature_cap_literal_not_hardcoded_in_api_or_frontend():
    """邊界②：硬編碼掃描 `== 0`（TODO Task 6.0 之驗收②逐字命令）。"""
    literal = ic_report_reason("analysis_rejected")
    assert literal                                          # 正向對照：真的取得到字面
    proc = subprocess.run(
        ["grep", "-rn", literal, "api/", "frontend/src/"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    hits = [
        line for line in proc.stdout.splitlines()
        if line.strip() and "ic_report_contract" not in line
    ]
    assert hits == [], f"api／frontend 不得硬寫 reason 字面：{hits}"


def test_gap3_ic_feature_cap_unknown_category_fails_closed():
    """未知分類 ⇒ raise，不 fallback（否則打錯分類名會靜默拿到空清單）。"""
    import pytest

    with pytest.raises(KeyError):
        ic_report_reasons("no_such_category")
