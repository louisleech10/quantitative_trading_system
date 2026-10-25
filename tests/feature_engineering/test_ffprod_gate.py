"""FFPROD §G 改前基準對照（SPEC `docs/FFPROD_SPEC.md` §G、Task 0.2、Task 1.1 驗證、Phase 3 驗證）。

- `scripts/ffprod_freeze_baseline.py`：`freeze_cells`（邊界①②、L2 實際臂拒寫）、`compare`（逐位元＋`changed_targets` 精確集合）、
  `regenerate`（現行 HEAD 重生一格）、`GOLDEN_PATH`、`DECISIONS_PATH`。
- 重生案（`test_gate_regenerated_cells_match_frozen`）為真實 kline 生成，單行程串行；其餘為秒級契約案。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Mapping

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


def _cell(cell_id: str, **extra: Any) -> Dict[str, Any]:
    return {"id": cell_id, "kind": "A", "symbol": "BTCUSDT", "timeframes": ["1h"], "env": {}, **extra}


# ---------------------------------------------------------------------------------------------- 邊界（Task 0.2）

def test_boundary_01_interrupted_freeze_keeps_completed_cells_only(tmp_path: Path) -> None:
    fb = _load()
    out = tmp_path / "frozen.json"

    def generate(cell: Mapping[str, Any]) -> Dict[str, Any]:
        if cell["id"] == "c2":
            raise RuntimeError("中途中斷")
        return {"fingerprints": _fp({"x": "a"}), "identity": {"head": "h"}}

    with pytest.raises(RuntimeError, match="中途中斷"):
        fb.freeze_cells([_cell("c1"), _cell("c2")], out, generate=generate)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert set(written["cells"]) == {"c1"}


def test_boundary_02_hardware_blocked_cell_marked(tmp_path: Path) -> None:
    fb = _load()
    out = tmp_path / "frozen.json"

    def generate(cell: Mapping[str, Any]) -> Dict[str, Any]:
        if cell["id"] == "big":
            raise GenerationMemoryBudgetExceeded("逾 8 GB")
        return {"fingerprints": _fp({"x": "a"}), "identity": {"head": "h"}}

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
        return {"fingerprints": _fp({"x": "a"}), "identity": {"head": "h"}, "observed_arm": "L2.pandas_serial"}

    with pytest.raises(fb.ArmMismatch):
        fb.freeze_cells([cell], out, generate=generate)
    assert not out.exists() or "l2p" not in json.loads(out.read_text(encoding="utf-8")).get("cells", {})


def test_l2_arm_env_overrides_cover_three_arms() -> None:
    fb = _load()
    assert set(fb.L2_ARM_ENV) == {"L2.polars", "L2.pandas_serial", "L2.pandas_parallel"}
    assert fb.L2_ARM_ENV["L2.pandas_parallel"]["FFACT_L2_CATEGORY_WORKERS"] == "2"
    assert fb.L2_ARM_ENV["L2.pandas_serial"]["FFACT_L2_CATEGORY_WORKERS"] == "1"


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
    """§G：現行 HEAD 重生之每格值指紋對凍結值，只准 `decisions.json` 之 `changed_targets` 不等（Phase 1 前為空集合）。"""
    fb = _load()
    assert fb.GOLDEN_PATH.exists(), f"改前基準未凍結：{fb.GOLDEN_PATH}"
    frozen = json.loads(fb.GOLDEN_PATH.read_text(encoding="utf-8"))
    targets: Dict[str, set] = {}
    if fb.DECISIONS_PATH.exists():
        for item in json.loads(fb.DECISIONS_PATH.read_text(encoding="utf-8"))["candidates"]:
            if item.get("implemented_commit"):
                targets.setdefault("*", set()).update(item["changed_targets"])
    failures = []
    for cell in frozen["cell_list"]:
        entry = frozen["cells"][cell["id"]]
        if entry.get("status") == "blocked":
            continue
        actual = fb.regenerate(cell)["fingerprints"]
        failures += [f"{cell['id']}: {m}" for m in fb.compare(entry["fingerprints"], actual, targets.get("*", set()))]
    assert failures == []


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_compare_without_bitwise_keys_misses_value_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：比對鍵清空 ⇒ 單欄改值不再被抓到（證 `compare` 之判定確由 `BITWISE_KEYS` 承擔）。"""
    fb = _load()
    frozen, actual = _fp({"a": "1"}), _fp({"a": "2"})
    assert fb.compare(frozen, actual, set()) != []
    monkeypatch.setattr(fb, "BITWISE_KEYS", ())
    assert fb.compare(frozen, actual, set()) == []
