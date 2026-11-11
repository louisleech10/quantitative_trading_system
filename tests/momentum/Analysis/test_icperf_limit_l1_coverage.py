"""ICPERF SPEC v5.86 Task 0.6 (h)：L1 列↔測試對應之覆蓋檢查。

施工輸入＝L0 機讀表之不可變 git 物件 `1eeef821:tests/_golden/icperf/limit_inventory.json` 之 L1 needs_fix 列
（原始三元組 file、L0 line、完整 code_sha256；同 digest 之不同落點不合併）。
對應來源＝實際收集之測試（不以文字掃描）：
- pytest：於本行程以 `pytest.main(["--collect-only", ...])` 收集 `tests/momentum/Analysis/test_icperf_limit_l1*.py` 與
  `tests/api/test_icperf_limit_l1*.py`（L1b 起），
  取各 item 之 `limit_rows` 標記；帶 skip／xfail 標記之 item 不計。
- vitest：`npx vitest run --reporter=json` 實際執行 `frontend/src/**/*.limits.test.tsx`，取狀態為 passed 或 failed 之測試
  名稱中 `[rows:檔:L0 行:sha 前 12 碼,…]`（skipped／todo 不計）。
覆蓋檢查只證「每列有具名測試」之對應存在；斷言品質由測試本體與審碼保證（SPEC (h)）。
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

REPO = Path(__file__).resolve().parents[3]
L0_SPEC = "1eeef821:tests/_golden/icperf/limit_inventory.json"
Row = Tuple[str, int, str]


def _l0_l1_rows() -> Set[Row]:
    raw = subprocess.run(["git", "-C", str(REPO), "show", L0_SPEC], capture_output=True, check=True).stdout
    rows = json.loads(raw.decode("utf-8"))["rows"]
    return {(r["file"], int(r["line"]), r["code_sha256"]) for r in rows if r["needs_fix"] is True and r["batch"] == "L1"}


class _Collector:
    def __init__(self) -> None:
        self.rows: List[Tuple[str, Row]] = []

    def pytest_collection_modifyitems(self, items: List[Any]) -> None:
        for item in items:
            if item.get_closest_marker("skip") or item.get_closest_marker("skipif") or item.get_closest_marker("xfail"):
                continue
            for m in item.iter_markers("limit_rows"):
                for row in m.args:
                    self.rows.append((item.nodeid, (str(row[0]), int(row[1]), str(row[2]))))


def _pytest_declared() -> List[Tuple[str, Row]]:
    # ICPERF L1b（審查 r166 GROK-R166-P2-01）：路由層之 limit_rows 宣告位於 tests/api
    files = sorted(str(p) for d in (REPO / "tests" / "momentum" / "Analysis", REPO / "tests" / "api")
                   for p in d.glob("test_icperf_limit_l1*.py") if p.name != Path(__file__).name)
    col = _Collector()
    rc = pytest.main(["--collect-only", "-q", "-p", "no:cacheprovider", *files], plugins=[col])
    assert rc == 0, f"收集失敗 rc={rc}"
    return col.rows


def _vitest_declared(l0: Set[Row]) -> List[Tuple[str, Row]]:
    files = sorted(str(p.relative_to(REPO / "frontend")) for p in (REPO / "frontend" / "src").rglob("*.limits.test.tsx"))
    if not files:
        return []
    with tempfile.TemporaryDirectory(prefix="limit_l1_cov_") as td:
        out = Path(td) / "report.json"
        subprocess.run(["npx", "vitest", "run", "--reporter=json", f"--outputFile={out}", *files],
                       cwd=REPO / "frontend", capture_output=True)
        report = json.loads(out.read_text(encoding="utf-8"))
    by_prefix: Dict[Tuple[str, int, str], Row] = {(f, ln, sha[:12]): (f, ln, sha) for f, ln, sha in l0}
    found: List[Tuple[str, Row]] = []
    for suite in report["testResults"]:
        for res in suite["assertionResults"]:
            if res["status"] not in ("passed", "failed"):
                continue
            for m in re.finditer(r"\[rows:([^\]]+)\]", res["fullName"]):
                for tok in m.group(1).split(","):
                    f, ln, prefix = tok.rsplit(":", 2)
                    row = by_prefix.get((f, int(ln), prefix))
                    assert row is not None, f"{res['fullName'][:80]}：{tok} 不在 L0 L1 needs_fix 列"
                    found.append((res["fullName"], row))
    return found


@pytest.fixture(scope="module")
def l0() -> Set[Row]:
    return _l0_l1_rows()


@pytest.fixture(scope="module")
def declared(l0: Set[Row]) -> List[Tuple[str, Row]]:
    return _pytest_declared() + _vitest_declared(l0)


def test_l0_snapshot_is_the_committed_l1_set(l0: Set[Row]) -> None:
    """L0 固定輸入：不可變 git 物件之 L1 needs_fix 列共 305 落點、271 個 file＋sha 鍵（L0 提交 1eeef821 之實測）。"""
    assert len(l0) == 305
    assert len({(f, s) for f, _, s in l0}) == 271


def test_every_declared_row_is_an_l0_l1_row(l0: Set[Row], declared: List[Tuple[str, Row]]) -> None:
    """每個測試宣告之三元組皆為 L0 之 L1 needs_fix 列（禁指向不存在或非 L1 之列）。"""
    bad = [(nid, row) for nid, row in declared if row not in l0]
    assert not bad, bad[:5]
    assert declared, "未收集到任何 limit_rows 宣告"


L1A_FILES = ("momentum/Analysis/ic_config_schema.py", "frontend/src/components/ic-analysis/ICConfigPanel.tsx",
             "api/models/ic_models.py", "momentum/Analysis/net_ic_analyzer.py", "momentum/Analysis/turnover_analyzer.py",
             "frontend/src/components/ic-analysis/DeepAnalysisConfigPanel.tsx")


def test_l1a_rows_fully_covered(l0: Set[Row], declared: List[Tuple[str, Row]]) -> None:
    """L1a 子批：上列六檔之 L1 needs_fix 列（36 落點；DeepAnalysisConfigPanel 成本輸入依審查 r163 CODEX-R163-P1-01 納入）逐一有具名測試。"""
    target = {r for r in l0 if r[0] in L1A_FILES}
    assert len(target) == 36
    missing = sorted(target - {row for _, row in declared})
    assert not missing, missing


L1B_ROWS = {
    ("api/core/config.py", 30, "3d09a2bc57da300f911c2161adf53bc1da22ee49668445015a87f09ba8028839"),
    ("api/routes/ic_analysis.py", 87, "119e531ebe6f0593fadcb0e5c8c6ab1a2fb6c847bc4d27d4bc2eac9017086c6b"),
    ("api/routes/ic_analysis.py", 89, "f1971768baf175f16ff63e47f719cbef67201fee4cb05261190b050012dc8862"),
    ("api/routes/ic_analysis.py", 453, "f1971768baf175f16ff63e47f719cbef67201fee4cb05261190b050012dc8862"),
    ("frontend/src/components/ic-analysis/FeatureFilterPanel.tsx", 99,
     "343dd1a589c858e99f90c06356a13f7431d94e637610812a476d5e85255d5be8"),
}


def test_l1b_rows_fully_covered(l0: Set[Row], declared: List[Tuple[str, Row]]) -> None:
    """L1b 子批（IC 分析啟動入口；SPEC v5.87 (h)「⑤ IC 分析啟動准入」）：五落點皆為 L0 L1 列且逐一有具名測試
    （年份閘 ic_engine.py:1529 依裁定改列 L2，不在本子批）。"""
    assert L1B_ROWS <= l0
    missing = sorted(L1B_ROWS - {row for _, row in declared})
    assert not missing, missing


def _rebatched_out_of_l1() -> Set[Tuple[str, str]]:
    """現行裁定檔中已依 SPEC 改列 L2 之 (file, code_sha256)（例：年份閘依 SPEC (e) 改 L2，諮詢 r165 C8）。"""
    rulings = json.loads((REPO / "tests" / "_golden" / "icperf" / "limit_rulings.json").read_text(encoding="utf-8"))
    return {(r["file"], r["code_sha256"]) for r in rulings["rulings"] if r.get("needs_fix") is True and r.get("batch") == "L2"}


def test_rebatched_rows_are_named() -> None:
    """改列 L2 之 L0 L1 列逐一具名（禁以重分類靜默縮小 L1 目標）：現行只有年份閘一列。"""
    l0_keys = {(f, s) for f, _, s in _l0_l1_rows()}
    assert _rebatched_out_of_l1() & l0_keys == {
        ("momentum/Analysis/ic_engine.py", "57df8bcd34dedafabacc4a47289dabfdd3a3b8be8fdc71720524951e6d547c90")}


@pytest.mark.xfail(strict=True, reason="L1 收案前其餘子批尚未施工；全部 L1 落點（扣除依裁定改列 L2 者）皆有具名測試時本測試轉綠，strict 使其強制移除 xfail")
def test_all_l1_rows_covered(l0: Set[Row], declared: List[Tuple[str, Row]]) -> None:
    """L1 收案條件之一：全部 L1 needs_fix 落點（扣除依裁定改列 L2 者）皆有具名測試。"""
    rebatched = _rebatched_out_of_l1()
    target = {r for r in l0 if (r[0], r[2]) not in rebatched}
    missing = sorted(target - {row for _, row in declared})
    assert not missing, f"尚缺 {len(missing)} 落點"
