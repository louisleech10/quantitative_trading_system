"""governance 套件層 fixture。

P1-6 Task 3.1/3.2：預設隔離 DEBT_AUDIT_OVERRIDE 至空 audit，避免開發機
真實 .claude/gate/audit.log 留有 OPEN 債時整包假紅（SPEC Task 3.2 改法④）。

子程序若 `env=os.environ.copy()` 會繼承此隔離；hermetic 完整置換 env 的測試
（test_debt_*）自行帶 DEBT_AUDIT_OVERRIDE，不受影響。
刻意 pop GOVERNANCE_TEST_HARNESS 的反 bypass 測試仍可 pop 掉 harness。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_debt_audit_env(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """預設空 audit + harness，避免 ambient OPEN 債污染 gate 派工測試。"""
    # 已由外層明確指定者尊重（例如手動跑單一案例指向真 audit）
    if "DEBT_AUDIT_OVERRIDE" in __import__("os").environ:
        return
    audit_dir = tmp_path_factory.mktemp("gov_debt_audit")
    audit = Path(audit_dir) / "audit.log"
    audit.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEBT_AUDIT_OVERRIDE", str(audit))
    monkeypatch.setenv("GOVERNANCE_TEST_HARNESS", "1")
