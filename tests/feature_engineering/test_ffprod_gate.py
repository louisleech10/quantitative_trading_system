"""FFPROD §G 改前基準對照（SPEC `docs/FFPROD_SPEC.md` §G、Task 0.2、Task 1.1 驗證、Phase 3 驗證）。

- `scripts/ffprod_freeze_baseline.py`：`freeze_cells`（邊界①②、L2 實際臂拒寫）、`compare`（逐位元＋`changed_targets` 精確集合）、
  `regenerate`（現行 HEAD 重生一格）、`GOLDEN_PATH`、`DECISIONS_PATH`。
- 重生案（`test_gate_regenerated_cells_match_frozen`）為真實 kline 生成，單行程串行；其餘為秒級契約案。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

from momentum.FeatureEngineering.memory_budget import GenerationMemoryBudgetExceeded

REPO = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO / "scripts" / "ffprod_freeze_baseline.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("ffprod_freeze_baseline_under_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fp(values: Mapping[str, str]) -> Dict[str, Any]:
    """最小值指紋（契約案用；欄 → values_native 雜湊字面）。"""
    columns = {name: {"dtype": "float32", "nan": "n0", "values_native": v} for name, v in values.items()}
    order = list(values)
    return {"columns": columns, "column_set_sha256": "|".join(sorted(order)), "column_order_sha256": "|".join(order)}


#: 契約案之完整生成身分（SPEC Task 0.2：HEAD、設定、資料集 sha256）。
_IDENTITY = {"head": "h", "config_sha256": "c", "dataset_sha256": "d"}


def _cell(cell_id: str, **extra: Any) -> Dict[str, Any]:
    return {"id": cell_id, "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"], "env": {}, **extra}


# ---------------------------------------------------------------------------------------------- 邊界（Task 0.2）

def test_boundary_01_interrupted_freeze_keeps_completed_cells_only(tmp_path: Path) -> None:
    fb = _load()
    out = tmp_path / "frozen.json"

    def generate(cell: Mapping[str, Any]) -> Dict[str, Any]:
        if cell["id"] == "c2":
            raise RuntimeError("中途中斷")
        return {"fingerprints": _fp({"x": "a"}), "identity": dict(_IDENTITY)}

    with pytest.raises(RuntimeError, match="中途中斷"):
        fb.freeze_cells([_cell("c1"), _cell("c2")], out, generate=generate)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert set(written["cells"]) == {"c1"}


def test_boundary_02_hardware_blocked_cell_marked(tmp_path: Path) -> None:
    fb = _load()
    out = tmp_path / "frozen.json"

    def generate(cell: Mapping[str, Any]) -> Dict[str, Any]:
        if cell["id"] == "big":
            raise GenerationMemoryBudgetExceeded("big", 6 << 30, 3 << 30, 8 << 30, "逾 8 GB")
        return {"fingerprints": _fp({"x": "a"}), "identity": dict(_IDENTITY)}

    fb.freeze_cells([_cell("big"), _cell("small")], out, generate=generate)
    written = json.loads(out.read_text(encoding="utf-8"))["cells"]
    assert written["big"] == {"status": "blocked", "blocked_by": fb.BLOCKED_BY_HARDWARE}
    assert "fingerprints" in written["small"]


# ---------------------------------------------------------------------------------------------- 驗證

def test_l2_cell_arm_mismatch_refused(tmp_path: Path) -> None:
    fb = _load()
    out = tmp_path / "frozen.json"
    cell = _cell("l2p", declared_arm="L2.pandas_parallel", env=fb.L2_ARM_ENV["L2.pandas_parallel"])

    def generate(_cell: Mapping[str, Any]) -> Dict[str, Any]:
        return {"fingerprints": _fp({"x": "a"}), "identity": dict(_IDENTITY), "observed_arm": "L2.pandas_serial"}

    with pytest.raises(fb.ArmMismatch):
        fb.freeze_cells([cell], out, generate=generate)
    assert not out.exists() or "l2p" not in json.loads(out.read_text(encoding="utf-8")).get("cells", {})


def test_l2_arm_env_overrides_cover_three_arms() -> None:
    fb = _load()
    assert set(fb.L2_ARM_ENV) == {"L2.polars", "L2.pandas_serial", "L2.pandas_parallel"}
    assert fb.L2_ARM_ENV["L2.pandas_parallel"]["FFACT_L2_CATEGORY_WORKERS"] == "2"
    assert fb.L2_ARM_ENV["L2.pandas_serial"]["FFACT_L2_CATEGORY_WORKERS"] == "1"


#: SPEC Task 0.2 改法之最少路徑集合（每格以 `covers` 宣告其獨有覆蓋；全部格之聯集須恰含下列各項）。
REQUIRED_COVERAGE = {
    "A_1h", "A_12h", "B_1h_4h", "C_1h", "winsor_sigma", "fracdiff_adf",
    "L2.polars", "L2.pandas_serial", "L2.pandas_parallel",
}


def _pre(cell: Mapping[str, Any]) -> Mapping[str, Any]:
    return cell.get("preprocessing", {})


#: 每個覆蓋標記之結構判準（只由格之 `kind`／`timeframes`／`preprocessing`／`declared_arm`／`env` 導出，不信 `covers` 自述）。
COVERAGE_PREDICATES = {
    "A_1h": lambda c, fb: c["kind"] == "A" and list(c["timeframes"]) == ["1h"],
    "A_12h": lambda c, fb: c["kind"] == "A" and list(c["timeframes"]) == ["12h"],
    "B_1h_4h": lambda c, fb: c["kind"] == "B" and list(c["timeframes"]) == ["1h", "4h"],
    "C_1h": lambda c, fb: c["kind"] == "C" and list(c["timeframes"]) == ["1h"],
    "winsor_sigma": lambda c, fb: _pre(c).get("winsorization", {}).get("method") == "sigma",
    "fracdiff_adf": lambda c, fb: bool(_pre(c).get("fractional_differencing")) and bool(_pre(c).get("adf_differencing")),
    **{arm: (lambda c, fb, arm=arm: c.get("declared_arm") == arm
             and all(c["env"].get(k) == v for k, v in fb.L2_ARM_ENV[arm].items()))
       for arm in ("L2.polars", "L2.pandas_serial", "L2.pandas_parallel")},
}


def coverage_errors(cell_list: Any, fb: Any) -> List[str]:
    """`covers` 每個標記須滿足其結構判準；每個必需標記須至少一格以結構判準成立；格 id 唯一。"""
    errors = []
    ids = [c["id"] for c in cell_list]
    if len(ids) != len(set(ids)):
        errors.append("格 id 重複")
    for cell in cell_list:
        for tag in cell["covers"]:
            if tag not in COVERAGE_PREDICATES or not COVERAGE_PREDICATES[tag](cell, fb):
                errors.append(f"{cell['id']} 宣告 {tag} 而結構不符")
        arm = cell.get("declared_arm")
        if arm is not None:
            if arm not in fb.L2_ARM_ENV:
                errors.append(f"{cell['id']} 之 declared_arm {arm!r} 不屬 L2_ARM_ENV")
            elif arm not in cell["covers"] or not COVERAGE_PREDICATES[arm](cell, fb):
                errors.append(f"{cell['id']} 之 declared_arm {arm} 未列於自身 covers 或環境不符")
    for tag in sorted(REQUIRED_COVERAGE):
        if not any(tag in c["covers"] and COVERAGE_PREDICATES[tag](c, fb) for c in cell_list):
            errors.append(f"缺 {tag}")
    return errors


def test_cells_cover_required_paths() -> None:
    fb = _load()
    assert set(COVERAGE_PREDICATES) == REQUIRED_COVERAGE
    assert coverage_errors(fb.cells(), fb) == []


def test_mutation_single_cell_claiming_all_tags_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：`cells()` 退化為單格並自述全部標記 ⇒ 覆蓋案轉紅（結構判準不信自述）。"""
    fb = _load()
    lone = [_cell("only", covers=sorted(REQUIRED_COVERAGE))]
    monkeypatch.setattr(fb, "cells", lambda: lone)
    assert coverage_errors(fb.cells(), fb) != []


def test_cell_identity_required(tmp_path: Path) -> None:
    """SPEC Task 0.2「逐格生成並寫值指紋與生成身分（HEAD、設定、資料集 sha256）」：身分缺任一鍵 ⇒ 拒寫該格；
    齊全 ⇒ 寫入之身分與生成回傳逐鍵相同。"""
    fb = _load()
    full = dict(_IDENTITY)
    out = tmp_path / "frozen.json"
    fb.freeze_cells([_cell("ok")], out, generate=lambda _c: {"fingerprints": _fp({"x": "a"}), "identity": dict(full)})
    assert json.loads(out.read_text(encoding="utf-8"))["cells"]["ok"]["identity"] == full
    for missing in full:
        partial = {k: v for k, v in full.items() if k != missing}
        bad_out = tmp_path / f"bad_{missing}.json"
        with pytest.raises(ValueError):
            fb.freeze_cells([_cell("bad")], bad_out,
                            generate=lambda _c, p=partial: {"fingerprints": _fp({"x": "a"}), "identity": p})


def test_estimate_flag_only_estimates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC Task 0.2「先估時」：`main(["--estimate"])` 只呼叫 `estimate`，不呼叫 `freeze_cells`、不寫基準檔。"""
    fb = _load()
    calls: Dict[str, int] = {"estimate": 0, "freeze": 0}
    monkeypatch.setattr(fb, "GOLDEN_PATH", tmp_path / "golden.json")
    monkeypatch.setattr(fb, "cells", lambda: _complete_cells(fb))

    def fake_estimate(cell_list: Any) -> Dict[str, Any]:
        calls["estimate"] += 1
        return {"cells": {c["id"]: 1.0 for c in cell_list}, "total_seconds": float(len(cell_list))}

    def spy_freeze(*_a: Any, **_k: Any) -> Dict[str, Any]:
        calls["freeze"] += 1
        return {}

    monkeypatch.setattr(fb, "estimate", fake_estimate)
    monkeypatch.setattr(fb, "freeze_cells", spy_freeze)
    assert fb.main(["--estimate"]) == 0
    assert calls == {"estimate": 1, "freeze": 0}
    assert not fb.GOLDEN_PATH.exists()


def _complete_cells(fb: Any) -> List[Dict[str, Any]]:
    """滿足全部結構判準之最小格組（契約案用）。"""
    both = {"winsorization": {"method": "quantile"}, "fractional_differencing": True, "adf_differencing": True}
    cells = [
        {**_cell("a1", covers=["A_1h", "fracdiff_adf"]), "preprocessing": both},
        {**_cell("a12", timeframes=["12h"], covers=["A_12h"])},
        {**_cell("b", kind="B", timeframes=["1h", "4h"], covers=["B_1h_4h"])},
        {**_cell("c", kind="C", covers=["C_1h"])},
        {**_cell("sig", covers=["A_1h", "winsor_sigma"]), "preprocessing": {"winsorization": {"method": "sigma"}}},
    ]
    for arm, env in fb.L2_ARM_ENV.items():
        cells.append(_cell(arm, covers=["A_1h", arm], declared_arm=arm, env=dict(env)))
    return cells


def test_mutation_l2_cell_arm_binding_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：多一個漏標自身 arm 之 L2 格、或未知 arm 之格 ⇒ 覆蓋案轉紅；完整格組 ⇒ 綠。"""
    fb = _load()
    good = _complete_cells(fb)
    monkeypatch.setattr(fb, "cells", lambda: good)
    assert coverage_errors(fb.cells(), fb) == []
    unlabeled = _cell("extra", covers=["A_1h"], declared_arm="L2.pandas_parallel",
                      env=dict(fb.L2_ARM_ENV["L2.pandas_parallel"]))
    unknown = _cell("odd", covers=["A_1h"], declared_arm="L2.unknown", env={})
    for extra in (unlabeled, unknown):
        monkeypatch.setattr(fb, "cells", lambda e=extra: good + [e])
        assert coverage_errors(fb.cells(), fb) != []


def test_compare_exact_changed_targets() -> None:
    fb = _load()
    frozen = _fp({"a": "1", "b": "2"})
    assert fb.compare(frozen, _fp({"a": "1", "b": "2"}), set()) == []
    assert fb.compare(frozen, _fp({"a": "1", "b": "9"}), {"b"}) == []
    assert fb.compare(frozen, _fp({"a": "1", "b": "9"}), set()) != []      # 未核可之欄改值
    assert fb.compare(frozen, _fp({"a": "1", "b": "2"}), {"b"}) != []      # 核可之欄實際未改（少一欄）
    assert fb.compare(frozen, _fp({"b": "2", "a": "1"}), set()) != []      # 欄序不同
    assert fb.compare(frozen, _fp({"a": "1"}), set()) != []                # 欄集合不同


def test_gate_regenerated_cells_match_frozen() -> None:
    """§G（Phase 0–2、Phase 4）：現行 HEAD 重生之每格值指紋逐位元等於凍結值。於凍結 HEAD 跑即 SPEC Task 0.2「同格重跑
    兩次值指紋相同」（凍結為第一次、本案為第二次）。Phase 3 之逐候選／逐格對照依 Task 2.2 裁定於 SPEC 修訂版具體化
    （不得以全部候選 `changed_targets` 之聯集作全域放行），在此之前已有施工之決定 ⇒ 本案拒絕判定。"""
    fb = _load()
    assert fb.GOLDEN_PATH.exists(), f"改前基準未凍結：{fb.GOLDEN_PATH}"
    frozen = json.loads(fb.GOLDEN_PATH.read_text(encoding="utf-8"))
    if fb.DECISIONS_PATH.exists():
        implemented = [d["candidate_id"] for d in json.loads(fb.DECISIONS_PATH.read_text(encoding="utf-8"))["candidates"]
                       if d.get("implemented_commit")]
        assert implemented == [], f"Phase 3 對照尚未具體化（Task 3.x），已施工：{implemented}"
    failures = []
    for cell in frozen["cell_list"]:
        entry = frozen["cells"][cell["id"]]
        if entry.get("status") == "blocked":
            continue
        actual = fb.regenerate(cell)["fingerprints"]
        failures += [f"{cell['id']}: {m}" for m in fb.compare(entry["fingerprints"], actual, set())]
    assert failures == []


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_compare_without_bitwise_keys_misses_value_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：比對鍵清空 ⇒ 單欄改值不再被抓到（證 `compare` 之判定確由 `BITWISE_KEYS` 承擔）。"""
    fb = _load()
    frozen, actual = _fp({"a": "1"}), _fp({"a": "2"})
    assert fb.compare(frozen, actual, set()) != []
    monkeypatch.setattr(fb, "BITWISE_KEYS", ())
    assert fb.compare(frozen, actual, set()) == []
