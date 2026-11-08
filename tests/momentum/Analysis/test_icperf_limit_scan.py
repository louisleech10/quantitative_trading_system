"""ICPERF SPEC v5.84 Task 0.6 (a)(b)：上限盤點掃描器 `scripts/limit_scan.py` 與現行需修機讀表之測試（L0）。

被測（施工前不存在 ⇒ 本檔應為紅）：
- `scan(paths) -> {"rows": [{"file", "line", "kind", "value", "code"}...], "errors": [{"file", "error"}...]}`：
  Python（AST）、JSON、TS／TSX、YAML 各以語法解析；parse 失敗入 errors，不得視為「無上限」。
- `tests/_golden/icperf/limit_inventory.json`：每列 `file`、`line`、`code_sha256`、`category`、`semantic_type`、
  `needs_fix`、`batch`、`reason`、`g_impact`（{"kind": none|value|structure, "items": [§G 項]}）；`code_sha256` 須等於現行碼該行（去首尾空白）之 sha256（漂移即紅）。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "limit_scan.py"
INVENTORY = REPO / "tests" / "_golden" / "icperf" / "limit_inventory.json"
CATEGORIES = {"A", "B", "C", "D", "E", "F", "G"}
SEMANTIC = {"none", "1", "2", "3", "4", "5", "6", "7"}


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ls() -> Any:
    return _load("limit_scan_under_test", SCRIPT)


def _rows_at(out: Dict[str, Any], path: Path, line: int) -> List[Dict[str, Any]]:
    return [r for r in out["rows"] if Path(r["file"]).name == path.name and r["line"] == line]


G_ITEMS = {"ic_report", "stage5_subset", "deep_analysis", "event_report", "icfirst_post_ic", "ic_report_long",
           "deep_analysis_long", "event_import_report"}


def _assert_g_impact(g: Any) -> None:
    """SPEC (a)：`g_impact`＝{"kind": none|value|structure, "items": [§G 項...]}；none ⇔ items 為空。"""
    assert isinstance(g, dict) and set(g) == {"kind", "items"}, f"g_impact 形狀錯：{g!r}"
    assert g["kind"] in ("none", "value", "structure")
    assert set(g["items"]) <= G_ITEMS, f"未知 §G 項：{sorted(set(g['items']) - G_ITEMS)}"
    assert (g["kind"] == "none") == (len(g["items"]) == 0)


def _src(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_boundary_01_negative_slice(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "a.py", "def f(df):\n    return df.iloc[-500:]\n")
    rows = _rows_at(ls.scan([p]), p, 2)
    assert any(r["value"] in (500, -500) for r in rows), "UnaryOp 負切片須命中"


def test_boundary_02_non_le_keyword_arguments(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "b.py", "def g(m):\n    return m.top(top_n=20, sample_size=200, limit=2000)\n")
    vals = {r["value"] for r in _rows_at(ls.scan([p]), p, 2)}
    assert {20, 200, 2000} <= vals


def test_boundary_03_slice_of_one(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "c.py", "def h(xs):\n    return xs[:1]\n")
    assert any(r["value"] == 1 for r in _rows_at(ls.scan([p]), p, 2)), "`[:1]` 不得因排除 1 而漏"


def test_boundary_04_symbolic_constant_resolved_one_level(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "d.py", "LIMIT = 50\n\ndef k(xs):\n    return xs[:LIMIT]\n")
    rows = _rows_at(ls.scan([p]), p, 4)
    assert any(r["value"] == 50 for r in rows), "符號常數追一層宣告"


def test_boundary_05_json_contract_numbers(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "e.json", '{\n  "scan_grid_max_runs": {\n    "example_default": 110\n  }\n}\n')
    assert any(r["value"] == 110 for r in ls.scan([p])["rows"] if Path(r["file"]).name == "e.json")


def test_boundary_06_typescript_slice_and_number(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "f.tsx", "export const A = (xs: string[]) => xs.slice(0, 50);\nconst LIMIT = 1_000_000;\n")
    out = ls.scan([p])
    assert any(r["value"] == 50 for r in _rows_at(out, p, 1))
    assert any(r["value"] == 1000000 for r in _rows_at(out, p, 2))


def test_boundary_07_yaml_numbers(ls: Any, tmp_path: Path) -> None:
    p = _src(tmp_path, "g.yaml", "cpcv:\n  max_paths: 50\n")
    assert any(r["value"] == 50 for r in _rows_at(ls.scan([p]), p, 2))


@pytest.mark.parametrize("name,text", [
    ("bad.py", "def broken(:\n"),
    ("bad.json", '{"a": 1,,}\n'),
    ("bad.tsx", "export const A = ( => 1;\n"),
    ("bad.yaml", "a: [1, 2\n"),
])
def test_boundary_08_parse_failure_reported_not_empty(ls: Any, tmp_path: Path, name: str, text: str) -> None:
    bad = _src(tmp_path, name, text)
    out = ls.scan([bad])
    assert all(Path(r["file"]).name != name for r in out["rows"])
    assert any(Path(e["file"]).name == name for e in out["errors"]), f"{name} parse 失敗須入 errors，不得視為無上限"


def test_boundary_09_inventory_rows_well_formed_and_not_drifted() -> None:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = inv["rows"]
    assert rows, "機讀表不得為空"
    for r in rows:
        assert {"file", "line", "code_sha256", "category", "semantic_type", "needs_fix", "batch", "reason",
                "g_impact"} <= set(r)
        assert r["category"] in CATEGORIES and str(r["semantic_type"]) in SEMANTIC
        if r["needs_fix"]:
            assert r["batch"] in ("L1", "L2") and str(r["semantic_type"]) != "none"
        _assert_g_impact(r["g_impact"])
        if r["needs_fix"] and r["batch"] == "L1":
            assert r["g_impact"]["kind"] == "none", "L1 為不改輸出批，g_impact 須為 none"
        lines = (REPO / r["file"]).read_text(encoding="utf-8").splitlines()
        cur = lines[r["line"] - 1].strip()
        assert hashlib.sha256(cur.encode("utf-8")).hexdigest() == r["code_sha256"], f"{r['file']}:{r['line']} 已漂移"


def test_boundary_10_inventory_covers_both_blocks() -> None:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    fix_files = {r["file"] for r in inv["rows"] if r["needs_fix"]}
    assert any(f.startswith(("momentum/FeatureEngineering/", "api/services/feature_factory")) for f in fix_files), \
        "特徵生成塊須有需修列（使用者 2026-11-08 兩大塊）"
    assert any(f.startswith("momentum/Analysis/") for f in fix_files), "IC 分析塊須有需修列"
    assert not any(r["file"] == "api/models/ic_models.py" and "le=200" in r.get("reason", "") for r in inv["rows"]), \
        "已移除之 top_n le=200 不得重列"


def test_boundary_11_default_roots_full_candidate_set(ls: Any, tmp_path: Path) -> None:
    """迷你 repo：預設根遞迴、各語言與設定檔、parse 失敗，候選全集須恰等於預期（漏一即紅）。"""
    files = {
        "momentum/Analysis/a.py": "def f(df):\n    return df.iloc[-500:]\n",
        "momentum/Analysis/contracts/c.json": '{\n  "max_rows": 120000\n}\n',
        "api/models/m.py": "from pydantic import Field\nclass C:\n    n: int = Field(default=100, le=1000)\n",
        "frontend/src/b.tsx": "export const A = (xs: string[]) => xs.slice(0, 50);\n",
        "config/x.yaml": "cpcv:\n  max_paths: 50\n",
        "config/user_ic_config.yaml": "ic:\n  top_n: 30\n",
        "momentum/Analysis/bad.py": "def broken(:\n",
        "scripts/not_scanned.py": "x = [1, 2, 3][:2]\n",
    }
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    out = ls.scan_default_roots(tmp_path)
    got = {(r["file"], r["line"], r["value"]) for r in out["rows"]}
    expected = {("momentum/Analysis/a.py", 2, 500), ("momentum/Analysis/contracts/c.json", 2, 120000),
                ("api/models/m.py", 3, 100), ("api/models/m.py", 3, 1000), ("frontend/src/b.tsx", 1, 50),
                ("config/x.yaml", 2, 50), ("config/user_ic_config.yaml", 2, 30)}
    got_norm = {(f, ln, abs(v)) for f, ln, v in got}
    assert expected <= got_norm, f"漏候選：{sorted(expected - got_norm)}"
    assert not any(f.startswith("scripts/") for f, _, _ in got), "預設根外不掃"
    assert [e["file"] for e in out["errors"]] == ["momentum/Analysis/bad.py"]


def test_boundary_12_build_inventory_keeps_unruled(ls: Any, tmp_path: Path) -> None:
    p = tmp_path / "momentum" / "Analysis" / "a.py"
    p.parent.mkdir(parents=True)
    p.write_text("def f(df):\n    return df.iloc[-500:]\n\ndef g(xs):\n    return xs[:20]\n", encoding="utf-8")
    scan_out = ls.scan_default_roots(tmp_path)
    sha = hashlib.sha256("return df.iloc[-500:]".encode("utf-8")).hexdigest()
    g = {"kind": "value", "items": ["deep_analysis"]}
    rulings = {"rulings": [{"file": "momentum/Analysis/a.py", "code_sha256": sha, "category": "A", "semantic_type": "1",
                            "needs_fix": True, "batch": "L2", "reason": "規模截斷", "g_impact": g},
                           {"file": "momentum/Analysis/gone.py", "code_sha256": "0" * 64, "category": "B",
                            "semantic_type": "2", "needs_fix": True, "batch": "L1", "reason": "已不存在",
                            "g_impact": {"kind": "none", "items": []}}]}
    inv = ls.build_inventory(scan_out, rulings, tmp_path)
    assert [(r["file"], r["line"]) for r in inv["rows"]] == [("momentum/Analysis/a.py", 2)]
    row = inv["rows"][0]
    assert row["reason"] == "規模截斷" and row["g_impact"] == g and row["code_sha256"] == sha, "裁定欄位須原樣保留"
    unruled = inv["unruled"]
    assert any(u.get("file") == "momentum/Analysis/a.py" and u.get("line") == 5 for u in unruled), "無裁定之候選須列出"
    assert any(u.get("file") == "momentum/Analysis/gone.py" for u in unruled), "指向不存在候選之裁定須列出"


def test_boundary_13_committed_inventory_reproducible(ls: Any) -> None:
    """以同一生成端重產現行機讀表：列集合須等於受版控檔；且無未裁定之候選殘留。"""
    rulings = json.loads((REPO / "tests" / "_golden" / "icperf" / "limit_rulings.json").read_text(encoding="utf-8"))
    regen = ls.build_inventory(ls.scan_default_roots(REPO), rulings, REPO)
    committed = json.loads(INVENTORY.read_text(encoding="utf-8"))["rows"]
    key = lambda r: (r["file"], r["line"], r["code_sha256"], r["category"], str(r["semantic_type"]),
                     r["needs_fix"], r["batch"], r["reason"], json.dumps(r["g_impact"], sort_keys=True))
    assert sorted(map(key, regen["rows"])) == sorted(map(key, committed))
    assert regen["unruled"] == [], f"尚有未裁定候選 {len(regen['unruled'])} 筆"


def test_mutation_scanner_dropping_negative_slice_detected(ls: Any, tmp_path: Path,
                                                           monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞 scan（濾掉負切片之列）⇒ boundary_01 之斷言翻紅。"""
    real = ls.scan

    def broken(paths: Any) -> Dict[str, Any]:
        out = real(paths)
        return {"rows": [r for r in out["rows"] if r["value"] not in (500, -500)], "errors": out["errors"]}

    monkeypatch.setattr(ls, "scan", broken)
    with pytest.raises(AssertionError):
        test_boundary_01_negative_slice(ls, tmp_path)
