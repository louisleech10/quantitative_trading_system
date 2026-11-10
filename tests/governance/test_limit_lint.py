"""ICPERF SPEC v5.85 Task 0.6 (g)：防上限 checker `scripts/limit_lint.py` 之測試（L3）。

被測（施工前不存在 ⇒ 本檔應為紅）：
- `lint_text(path, text) -> List[dict]`：每筆 `{"rule", "line", "symbol", "confidence"}`，confidence ∈ {"high", "hint"}；
  只檢產品路徑（`momentum/`、`api/`、`frontend/src/`、`config/`），測試檔與 scripts 不檢；parse 失敗回 rule="parse_error"。
  固定秒數中止計算由既有 NOCAP `timeout_write_guard` 負責，本 checker 不重複。
- 豁免：同行 `# limit-lint: allow=<rule> reason=<理由>`（TS 用 `//`），規則須為被命中者、理由不得空。
- CLI：`limit_lint.py --mode warn|block [--root <repo 根>] <檔>...`；warn 一律 rc 0 只印提示；block 對未豁免之 high 命中或
  parse_error rc 2。
L3 收案條件（SPEC 驗證段）另驗：掛載點與 `.claude/settings.json`／pre-commit 對證、`docs/GOV_ENFORCEMENT_REGISTRY.md` 已登記。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, List

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "limit_lint.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ll() -> Any:
    return _load("limit_lint_under_test", SCRIPT)


def _high(findings: List[dict]) -> List[dict]:
    return [f for f in findings if f["confidence"] == "high"]


def test_boundary_01_field_upper_bound_flagged(ll: Any) -> None:
    src = "from pydantic import Field\nclass C:\n    n: int = Field(default=100, ge=10, le=1000)\n"
    hits = _high(ll.lint_text("api/models/x.py", src))
    assert [h["rule"] for h in hits] == ["field_upper_bound"] and hits[0]["line"] == 3


def test_boundary_02_count_gate_flagged(ll: Any) -> None:
    src = "def f(features):\n    if len(features) > 20:\n        raise ValueError('too many')\n"
    assert [h["rule"] for h in _high(ll.lint_text("api/services/x.py", src))] == ["count_gate"]


def test_boundary_03_dimension_reduces_precision_flagged(ll: Any) -> None:
    src = "def f(budget, feats):\n    n_perm = min(1000, budget // len(feats))\n    return n_perm\n"
    assert [h["rule"] for h in _high(ll.lint_text("momentum/Analysis/x.py", src))] == ["dimension_reduces_precision"]


def test_boundary_04_slice_into_statistic_flagged(ll: Any) -> None:
    src = "def f(df):\n    return df.iloc[:, :100].corr()\n"
    assert [h["rule"] for h in _high(ll.lint_text("momentum/Analysis/x.py", src))] == ["slice_into_statistic"]


def test_boundary_05_negatives_not_high(ll: Any) -> None:
    src = ("from pydantic import Field\nclass C:\n    n: int = Field(default=30, ge=1)\n"
           "chunk_size = 5000\n"
           "def g(x):\n    if x.size < 2:\n        return None\n    return x\n")
    assert _high(ll.lint_text("momentum/Analysis/x.py", src)) == [], "數學下限、分塊大小、定義域檢查不得為 high"


def test_boundary_06_test_files_and_non_product_paths_skipped(ll: Any) -> None:
    src = "from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n"
    assert ll.lint_text("tests/momentum/test_x.py", src) == []
    assert ll.lint_text("scripts/tool.py", src) == []


def test_boundary_07_inline_allow_requires_rule_and_reason(ll: Any) -> None:
    ok = ("from pydantic import Field\nclass C:\n"
          "    a: float = Field(gt=0, lt=1)  # limit-lint: allow=field_upper_bound reason=顯著水準數學值域\n")
    assert _high(ll.lint_text("api/models/x.py", ok)) == []
    no_reason = ("from pydantic import Field\nclass C:\n"
                 "    a: float = Field(gt=0, lt=1)  # limit-lint: allow=field_upper_bound\n")
    assert _high(ll.lint_text("api/models/x.py", no_reason)), "無理由之豁免無效"
    wrong_rule = ("from pydantic import Field\nclass C:\n"
                  "    a: float = Field(gt=0, lt=1)  # limit-lint: allow=count_gate reason=x\n")
    assert _high(ll.lint_text("api/models/x.py", wrong_rule)), "豁免須指定被命中之規則"


def test_boundary_08_parse_error_reported(ll: Any) -> None:
    hits = ll.lint_text("momentum/Analysis/x.py", "def broken(:\n")
    assert any(h["rule"] == "parse_error" for h in hits)


def test_boundary_09_cli_warn_vs_block(tmp_path: Path) -> None:
    p = tmp_path / "momentum" / "Analysis" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n", encoding="utf-8")
    warn = subprocess.run([sys.executable, str(SCRIPT), "--mode", "warn", "--root", str(tmp_path), str(p)],
                          capture_output=True, text=True)
    assert warn.returncode == 0 and "field_upper_bound" in (warn.stdout + warn.stderr)
    block = subprocess.run([sys.executable, str(SCRIPT), "--mode", "block", "--root", str(tmp_path), str(p)],
                           capture_output=True, text=True)
    assert block.returncode == 2


def _mounted_command() -> str:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    post = settings.get("hooks", {}).get("PostToolUse", [])
    cmds = [h.get("command", "") for m in post if "Edit" in m.get("matcher", "") and "Write" in m.get("matcher", "")
            for h in m.get("hooks", []) if "limit_lint" in h.get("command", "")]
    assert len(cmds) == 1, "PostToolUse Edit|Write 須恰掛一個 limit_lint 命令"
    return cmds[0]


def test_boundary_10_mounted_command_blocks_real_write(tmp_path: Path) -> None:
    """以 settings.json 實際掛載之命令（非字串存在）處理一次 PostToolUse 寫入事件：高信心違例 ⇒ 非 0；合法 ⇒ 0。"""
    cmd = _mounted_command()
    p = tmp_path / "momentum" / "Analysis" / "x.py"
    p.parent.mkdir(parents=True)

    def run(text: str) -> int:
        p.write_text(text, encoding="utf-8")
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(p), "content": text}})
        env = {"PATH": "/usr/bin:/bin", "LIMIT_LINT_ROOT": str(tmp_path), "HOME": str(tmp_path)}
        return subprocess.run(["bash", "-c", cmd], input=payload, capture_output=True, text=True,
                              cwd=REPO, env=env).returncode

    assert run("from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n") != 0, "掛載命令須擋高信心違例"
    assert run("from pydantic import Field\nclass C:\n    n: int = Field(ge=1)\n") == 0, "合法寫入不得被擋"


STAGED_HOOK = REPO / "scripts" / "git_hooks" / "limit_lint_staged.sh"


def test_boundary_11_staged_mode_exit_code_and_pre_commit_wiring(tmp_path: Path) -> None:
    """pre-commit 掛載之專用腳本實際執行於暫存庫：staged 違例 ⇒ 非 0；staged 合法 ⇒ 0；pre-commit 有一行實際執行它。"""
    hook_lines = (REPO / "scripts" / "git_hooks" / "pre-commit").read_text(encoding="utf-8").splitlines()
    live = [ln for ln in hook_lines if "limit_lint_staged.sh" in ln and not ln.lstrip().startswith("#")]
    assert len(live) == 1 and live[0].split()[0] in ("bash", '"$REPO_ROOT"/scripts/git_hooks/limit_lint_staged.sh',
                                                       "scripts/git_hooks/limit_lint_staged.sh"), \
        "pre-commit 須以一行實際執行 limit_lint_staged.sh（非 echo／註解）"
    assert "|| true" not in live[0] and "exit 0" not in live[0], "不得吞掉退出碼"
    staged_src = STAGED_HOOK.read_text(encoding="utf-8")
    assert "--mode block" in staged_src and "--staged" in staged_src, "pre-commit 須以 block 模式檢暫存區"
    repo = tmp_path / "r"
    (repo / "momentum" / "Analysis").mkdir(parents=True)
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)
    git("init", "-q")
    target = repo / "momentum" / "Analysis" / "x.py"

    def staged_rc(text: str) -> int:
        target.write_text(text, encoding="utf-8")
        git("add", "momentum/Analysis/x.py")
        env = {"PATH": "/usr/bin:/bin", "LIMIT_LINT_PY": sys.executable, "LIMIT_LINT_SCRIPT": str(SCRIPT),
               "HOME": str(tmp_path)}
        return subprocess.run(["bash", str(STAGED_HOOK)], capture_output=True, text=True, cwd=repo, env=env).returncode

    assert staged_rc("from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n") != 0
    assert staged_rc("from pydantic import Field\nclass C:\n    n: int = Field(ge=1)\n") == 0


def test_boundary_15_registry_lists_each_warn_rule() -> None:
    rec = json.loads((REPO / "tests" / "_golden" / "icperf" / "limit_lint_corpus_receipt.json").read_text(encoding="utf-8"))
    reg = (REPO / "docs" / "GOV_ENFORCEMENT_REGISTRY.md").read_text(encoding="utf-8")
    assert "limit_lint" in reg
    for r in rec["rules"]:
        if r["status"] == "warn":
            seg = reg[reg.find(r["rule"]):] if r["rule"] in reg else ""
            assert seg and "尚未阻擋" in seg[:400] and "升級條件" in seg[:400], f"warn 規則 {r['rule']} 須具名登記原因與升級條件"


@pytest.mark.parametrize("path,src,rule", [
    ("api/routes/x.py", "from fastapi import Query\ndef f(n: int = Query(10, ge=1, le=500)):\n    return n\n",
     "field_upper_bound"),
    ("api/routes/y.py", "from fastapi import Query\ndef f(n: int = Query(10, ge=1, lt=500)):\n    return n\n",
     "field_upper_bound"),
    ("api/models/x.py", "from pydantic import Field\nclass C:\n    a: float = Field(gt=0, lt=0.5)\n", "field_upper_bound"),
    ("momentum/Analysis/x.py", "def f(cands):\n    if len(cands) > 200:\n        return None\n    return cands\n",
     "count_gate"),
    ("momentum/Analysis/x.py",
     "def f(groups):\n    for g in groups:\n        if len(g) > 5000:\n            continue\n        yield g\n", "count_gate"),
    ("api/services/x.py", "import json\ndef f(imp, fh):\n    json.dump(imp.index[:20].tolist(), fh)\n",
     "slice_into_statistic"),
])
def test_boundary_16_each_high_rule_branch(ll: Any, path: str, src: str, rule: str) -> None:
    assert rule in [h["rule"] for h in _high(ll.lint_text(path, src))], f"{rule} 須命中：{src!r}"


@pytest.mark.parametrize("path,src", [
    ("frontend/src/components/x.tsx", "export const A = (xs: string[]) => xs.slice(0, 50);\n"),
    ("config/x.yaml", "cpcv:\n  max_paths: 50\n"),
    ("momentum/Analysis/contracts/x.json", "{\"scan_cube_max_rows\": 120000}\n"),
])
def test_boundary_17_other_languages_valid_inputs_give_hints_not_high(ll: Any, path: str, src: str) -> None:
    hits = ll.lint_text(path, src)
    assert hits and all(h["confidence"] == "hint" for h in hits) and not any(h["rule"] == "parse_error" for h in hits), \
        "合法之 TS／YAML／JSON 上限候選須出提示（hint），不得空、不得為 parse_error"


@pytest.mark.parametrize("path,src", [
    ("frontend/src/components/x.tsx", "export const A = (xs: string[]) => xs.map((x) => x + 1);\n"),
    ("config/x.yaml", "name: demo\nenabled: true\n"),
    ("momentum/Analysis/contracts/x.json", "{\"label\": \"demo\"}\n"),
])
def test_boundary_18_other_languages_clean_inputs_no_findings(ll: Any, path: str, src: str) -> None:
    assert ll.lint_text(path, src) == []


@pytest.mark.parametrize("status,expected_rc", [("warn", 0), ("block", 2)])
def test_boundary_20_block_mode_follows_receipt_rule_status(tmp_path: Path, status: str, expected_rc: int) -> None:
    """block 模式只阻擋語料收據中 status＝block 之規則：同一 high 命中，規則為 warn ⇒ rc 0（只提示），block ⇒ rc 2。"""
    p = tmp_path / "momentum" / "Analysis" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n", encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"rules": [{"rule": "field_upper_bound", "status": status, "precision": 1.0,
                                              "recall": 1.0, "false_positives": [], "false_negatives": [],
                                              "accept_reason": "測試"}]}), encoding="utf-8")
    res = subprocess.run([sys.executable, str(SCRIPT), "--mode", "block", "--receipt", str(receipt),
                          "--root", str(tmp_path), str(p)], capture_output=True, text=True)
    assert res.returncode == expected_rc
    assert "field_upper_bound" in (res.stdout + res.stderr), "warn 規則仍須提示"


def test_boundary_19_cli_hint_passes_parse_error_blocks(tmp_path: Path) -> None:
    hint = tmp_path / "frontend" / "src" / "x.tsx"
    hint.parent.mkdir(parents=True)
    hint.write_text("export const A = (xs: string[]) => xs.slice(0, 50);\n", encoding="utf-8")
    run = lambda p: subprocess.run([sys.executable, str(SCRIPT), "--mode", "block", "--root", str(tmp_path), str(p)],
                                   capture_output=True, text=True).returncode
    assert run(hint) == 0, "hint 不阻擋"
    bad = tmp_path / "momentum" / "Analysis" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("def broken(:\n", encoding="utf-8")
    assert run(bad) == 2, "parse_error 於 block 模式阻擋"


def test_boundary_12_only_added_or_modified_lines(ll: Any) -> None:
    old = "from pydantic import Field\nclass C:\n    n: int = Field(le=1000)\n    m: int = 1\n"
    new_other = "from pydantic import Field\nclass C:\n    n: int = Field(le=1000)\n    m: int = 2\n"
    assert _high(ll.lint_changed("api/models/x.py", old, new_other)) == [], "未修改之舊違例不阻擋"
    new_value = "from pydantic import Field\nclass C:\n    n: int = Field(le=2000)\n    m: int = 1\n"
    assert [h["rule"] for h in _high(ll.lint_changed("api/models/x.py", old, new_value))] == ["field_upper_bound"], \
        "既有常數改值須檢"


@pytest.mark.parametrize("path,text", [
    ("frontend/src/components/x.tsx", "export const A = ( => 1;\n"),
    ("config/x.yaml", "a: [1, 2\n"),
    ("momentum/Analysis/contracts/x.json", "{\"a\": 1,,}\n"),
])
def test_boundary_13_each_language_parsed(ll: Any, path: str, text: str) -> None:
    assert any(h["rule"] == "parse_error" for h in ll.lint_text(path, text)), f"{path} 須以該語言語法解析"


def test_boundary_14_corpus_receipt_per_rule() -> None:
    rec = json.loads((REPO / "tests" / "_golden" / "icperf" / "limit_lint_corpus_receipt.json").read_text(encoding="utf-8"))
    rules = {r["rule"]: r for r in rec["rules"]}
    assert {"field_upper_bound", "count_gate", "dimension_reduces_precision", "slice_into_statistic"} <= set(rules)
    for name, r in rules.items():
        assert {"status", "precision", "recall", "false_positives", "false_negatives", "accept_reason"} <= set(r), name
        assert r["status"] in ("warn", "block")
    assert any(r["status"] == "block" for r in rules.values()), "L3 收案須至少一條高信心規則為 block"


@pytest.mark.parametrize("bound", ["2", "8", "9"])
def test_boundary_21_count_gate_small_numeric_bound(ll: Any, bound: str) -> None:
    """審碼 r153 CODEX-R153-P1-01：個位數之列欄數上限同為逾量即拒，不以數字大小推定為定義域。"""
    src = f"def f(features):\n    if len(features) > {bound}:\n        raise ValueError('too many')\n"
    assert [h["rule"] for h in _high(ll.lint_text("api/services/x.py", src))] == ["count_gate"]


@pytest.mark.parametrize("src", [
    "def f(xs):\n    if len(xs) <= 50:\n        return xs\n    else:\n        raise ValueError('too many')\n",
    "def f(xs):\n    if len(xs) > 50:\n        if True:\n            raise ValueError('too many')\n    return xs\n",
    "def f(xs):\n    if not (len(xs) <= 50):\n        return None\n    return xs\n",
    "def f(xs):\n    assert len(xs) <= 50\n    return xs\n",
    "import sys\ndef f(xs):\n    if len(xs) > 50:\n        sys.exit(1)\n    return xs\n",
])
def test_boundary_22_count_gate_rejection_variants(ll: Any, src: str) -> None:
    """審碼 r153 GROK-R153-P2-01：else 分支拒絕、巢狀拒絕、not 翻轉、assert、sys.exit 皆為逾量即拒。"""
    assert "count_gate" in [h["rule"] for h in _high(ll.lint_text("momentum/Analysis/x.py", src))], src


def test_boundary_23_changed_rejection_body_flags_unchanged_compare(ll: Any) -> None:
    """審碼 r153 CODEX-R153-P1-02：比較行未改、只把分支內容改成拒絕 ⇒ 屬新增之容量閘，須回報。"""
    old = "def f(features):\n    if len(features) > 20:\n        pass\n    return features\n"
    new = "def f(features):\n    if len(features) > 20:\n        raise ValueError('too many')\n    return features\n"
    assert [h["rule"] for h in _high(ll.lint_changed("momentum/Analysis/x.py", old, new))] == ["count_gate"]
    same = "def f(features):\n    if len(features) > 20:\n        raise ValueError('too many')\n    return features\n"
    assert _high(ll.lint_changed("momentum/Analysis/x.py", same, same + "\n# tail\n")) == [], "未改之舊違例不回報"


def test_boundary_24_dimension_rule_requires_precision_name(ll: Any) -> None:
    """審碼 r153 CODEX-R153-P2-01：一般平均值與依記憶體分塊不是精度參數，不得 high。"""
    src = ("def f(mem, cols, total, xs):\n    chunk_size = min(1000, mem // len(cols))\n"
           "    result = max(0.0, total / len(xs))\n    return chunk_size, result\n")
    assert _high(ll.lint_text("momentum/Analysis/x.py", src)) == []


@pytest.mark.parametrize("content", [None, "{", "{\"rules\": []}", "{\"rules\": [{\"rule\": \"field_upper_bound\"}]}"])
def test_boundary_25_block_mode_fail_closed_on_unusable_receipt(tmp_path: Path, content: Any) -> None:
    """審碼 r153 GROK-R153-P1-01／COMPOSER-R153-P2-01：收據缺檔、不可解析、空規則或缺 status ⇒ block 模式高信心命中一律擋。"""
    p = tmp_path / "momentum" / "Analysis" / "x.py"
    p.parent.mkdir(parents=True)
    p.write_text("from pydantic import Field\nclass C:\n    n: int = Field(le=5)\n", encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    if content is not None:
        receipt.write_text(content, encoding="utf-8")
    res = subprocess.run([sys.executable, str(SCRIPT), "--mode", "block", "--receipt", str(receipt),
                          "--root", str(tmp_path), str(p)], capture_output=True, text=True)
    assert res.returncode == 2, res.stderr


def test_boundary_26_allow_reason_requires_word_character(ll: Any) -> None:
    """審碼 r153 GROK-R153-P3-01：理由只有標點不算理由。"""
    src = ("from pydantic import Field\nclass C:\n"
           "    a: float = Field(gt=0, lt=1)  # limit-lint: allow=field_upper_bound reason=.\n")
    assert _high(ll.lint_text("api/models/x.py", src)), "reason=. 之豁免無效"


@pytest.mark.parametrize("src", [
    "TOO_MANY = object()\ndef f(xs):\n    if len(xs) > 8:\n        return TOO_MANY\n    return xs\n",
    "def f(xs, Response):\n    if len(xs) > 8:\n        return Response(status=413)\n    return xs\n",
    "def f(xs, lock):\n    if len(xs) > 8:\n        with lock:\n            raise ValueError('too many')\n    return xs\n",
    "def f(xs, cleanup):\n    if len(xs) > 8:\n        try:\n            raise ValueError('too many')\n        finally:\n            cleanup()\n    return xs\n",
])
def test_boundary_27_count_gate_sentinel_response_with_try(ll: Any, src: str) -> None:
    """審碼 r154 CODEX-R154-P1-01：哨兵、錯誤回應、with／try 內之拒絕皆為逾量即拒。"""
    assert "count_gate" in [h["rule"] for h in _high(ll.lint_text("momentum/Analysis/x.py", src))], src


@pytest.mark.parametrize("src", [
    "def f(xs, compute):\n    if len(xs) >= 2:\n        return compute(xs)\n    return None\n",
    "def f(xs, compute):\n    if len(xs) >= 2:\n        result = compute(xs)\n        return result\n    return None\n",
])
def test_boundary_28_count_gate_data_sufficient_return_not_high(ll: Any, src: str) -> None:
    """r154 修補之負例：回傳受量資料或分支內算出之結果為資料足量之正常路徑，不是拒絕。"""
    assert _high(ll.lint_text("momentum/Analysis/x.py", src)) == [], src


def test_boundary_29_changed_nested_condition_flags_gate(ll: Any) -> None:
    """審碼 r154 CODEX-R154-P1-02：只改拒絕路徑上之中間條件（False→True）即新增有效容量閘，須回報。"""
    old = "def f(xs):\n    if len(xs) > 8:\n        if False:\n            raise ValueError('too many')\n    return xs\n"
    new = old.replace("if False:", "if True:")
    assert [h["rule"] for h in _high(ll.lint_changed("momentum/Analysis/x.py", old, new))] == ["count_gate"]


@pytest.mark.parametrize("src", [
    "def f(xs, Response):\n    if len(xs) > 8:\n        error = Response(status=413)\n        return error\n    return xs\n",
    "def f(xs, Response):\n    if len(xs) > 8:\n        return Response(status=413, detail=str(len(xs)))\n    return xs\n",
    "def f(xs, compute):\n    if len(xs) > 8:\n        return compute(xs[:8])\n    return compute(xs)\n",
])
def test_boundary_30_count_gate_any_early_return_when_fallthrough_is_normal(ll: Any, src: str) -> None:
    """審碼 r155 CODEX-R155-P1-01：正常路徑在分支之後時，逾量分支之任何 return（變數承接之錯誤回應、
    帶資料之錯誤訊息、截斷後結果）皆為分流。"""
    assert "count_gate" in [h["rule"] for h in _high(ll.lint_text("momentum/Analysis/x.py", src))], src


@pytest.mark.parametrize("src", [
    "def f(p, fallback):\n    if len(p.parents) >= 3:\n        return p.parents[2]\n    return fallback\n",
    "def f(array):\n    if array.ndim == 2 and array.shape[1] >= 2:\n        return array[:, 1]\n    raise ValueError('bad')\n",
    "def f(parts, name):\n    if len(parts) >= 3:\n        return '_'.join([parts[0]] + parts[2:])\n    return name\n",
])
def test_boundary_33_index_guard_not_high(ll: Any, src: str) -> None:
    """r155 修補之負例：長度檢查保護常數索引取值，非上限。"""
    assert _high(ll.lint_text("momentum/Analysis/x.py", src)) == [], src


def test_boundary_31_changed_second_with_context_flags_gate(ll: Any) -> None:
    """審碼 r155 CODEX-R155-P1-02：只改 with 之第二個 context（吞例外→傳播）即新增容量拒絕，須回報。"""
    old = ("from contextlib import nullcontext, suppress\ndef f(xs, lock):\n    if len(xs) > 8:\n"
           "        with lock, suppress(ValueError):\n            raise ValueError('too many')\n    return xs\n")
    new = old.replace("with lock, suppress(ValueError):", "with lock, nullcontext():")
    assert [h["rule"] for h in _high(ll.lint_changed("momentum/Analysis/x.py", old, new))] == ["count_gate"]


def test_boundary_32_raise_swallowed_by_except_not_high(ll: Any) -> None:
    """審碼 r155 CODEX-R155-P2-01：try 內之 raise 由 except 承接即被吞，非拒絕。"""
    src = ("def f(xs, log):\n    if len(xs) > 8:\n        try:\n            raise ValueError('too many')\n"
           "        except ValueError:\n            log('noted')\n    return xs\n")
    assert _high(ll.lint_text("momentum/Analysis/x.py", src)) == []


def test_mutation_rule_disabled_detected(ll: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞 lint_text（濾掉 field_upper_bound）⇒ boundary_01 之斷言翻紅。"""
    real = ll.lint_text
    monkeypatch.setattr(ll, "lint_text", lambda path, text: [f for f in real(path, text)
                                                            if f["rule"] != "field_upper_bound"])
    with pytest.raises(AssertionError):
        test_boundary_01_field_upper_bound_flagged(ll)
