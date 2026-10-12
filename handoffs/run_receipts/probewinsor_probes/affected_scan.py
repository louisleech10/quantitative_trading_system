"""PROBEWINSOR Task 1.3：受影響既有測試之機械挑選（AST；唯讀）。

挑選規則（docs/PROBEWINSOR_SPEC.md §C 之變化只在三處：A 前處理總開關關＋縮尾開之生成；B 該子空間之 config_hash；
C 被改呼叫點對缺鍵設定之例外型別／容錯）：
  R1 檔內有「前處理總開關設為 False」之寫法：dict 字面 {"preprocessing": {... "enabled": False ...}}（含巢狀於任一層）、
     `X["preprocessing"]["enabled"] = False`、`X.preprocessing.enabled = False`、`PreprocessingConfig(enabled=False)`、
     `SimpleNamespace(...preprocessing=SimpleNamespace(enabled=False...))`、`{"enabled": False}` 指派給 `X["preprocessing"]`；
  R2 檔內直接引用被改之符號（名稱或屬性）：見 SYMBOLS；
  R3 R1 之檔若同時含 config_hash 字面，另標 hash（B 類）。
輸出：JSON（檔 → 命中規則與行號），寫至 argv[1]。只掃 git ls-files 之 tests/**/*.py（-z 切分）。
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SYMBOLS = {
    "_calibration_winsorizer", "_resolve_public_window", "_stationarity_config_enabled",
    "_build_l7_raw_preprocessing_metadata", "_resolve_l65_generation_mode", "_collect_l65_stack_bars",
    "_compute_config_hash", "preview_feature_count", "_estimate_preprocessing_multiplier",
    "estimate_max_warmup_bars", "l65_enabled", "_probe_gate_salt", "PROBE_L65_GATE_SALT",
}


def _is_false(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _dict_get(node: ast.Dict, key: str):
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


class Scan(ast.NodeVisitor):
    def __init__(self) -> None:
        self.r1: list = []
        self.r2: list = []
        self.has_hash = False

    def visit_Dict(self, node: ast.Dict) -> None:
        pre = _dict_get(node, "preprocessing")
        if isinstance(pre, ast.Dict) and _is_false(_dict_get(pre, "enabled")):
            self.r1.append(node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            # X["preprocessing"]["enabled"] = False ／ X.preprocessing.enabled = False
            if _is_false(node.value):
                if (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "enabled" and isinstance(target.value, ast.Subscript)
                        and isinstance(target.value.slice, ast.Constant) and target.value.slice.value == "preprocessing"):
                    self.r1.append(node.lineno)
                if (isinstance(target, ast.Attribute) and target.attr == "enabled"
                        and isinstance(target.value, ast.Attribute) and target.value.attr == "preprocessing"):
                    self.r1.append(node.lineno)
            # X["preprocessing"] = {"enabled": False, ...} ／ X.preprocessing = {...}
            is_pre_target = ((isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
                              and target.slice.value == "preprocessing")
                             or (isinstance(target, ast.Attribute) and target.attr == "preprocessing"))
            if is_pre_target and isinstance(node.value, ast.Dict) and _is_false(_dict_get(node.value, "enabled")):
                self.r1.append(node.lineno)
            # X.preprocessing = SimpleNamespace(enabled=False, ...) ／ X["preprocessing"] = Cfg(enabled=False)
            if (is_pre_target and isinstance(node.value, ast.Call)
                    and any(k.arg == "enabled" and _is_false(k.value) for k in node.value.keywords)):
                self.r1.append(node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name == "PreprocessingConfig" and any(k.arg == "enabled" and _is_false(k.value) for k in node.keywords):
            self.r1.append(node.lineno)
        for kw in node.keywords:
            if kw.arg != "preprocessing":
                continue
            if isinstance(kw.value, ast.Call):
                if any(k.arg == "enabled" and _is_false(k.value) for k in kw.value.keywords):
                    self.r1.append(node.lineno)
            elif isinstance(kw.value, ast.Dict) and _is_false(_dict_get(kw.value, "enabled")):
                self.r1.append(node.lineno)  # s2_payload(preprocessing={"enabled": False}) 等覆寫
            elif _is_false(kw.value):
                self.r1.append(node.lineno)  # s1_payload(arm, preprocessing=False) 等旗標參數（逐檔複核語意）
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in SYMBOLS:
            self.r2.append((node.lineno, node.id))

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in SYMBOLS:
            self.r2.append((node.lineno, node.attr))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and "config_hash" in node.value:
            self.has_hash = True


def main() -> int:
    out = Path(sys.argv[1])
    proc = subprocess.run(["git", "ls-files", "-z", "--", "tests"], cwd=str(REPO), capture_output=True)
    errors = []
    if proc.returncode != 0 or proc.stderr.strip():  # 清單取得失敗不得當成「0 檔」成功
        errors.append(f"git ls-files rc={proc.returncode}: {proc.stderr.decode('utf-8', 'replace').strip()}")
    files = sorted(p for p in proc.stdout.decode("utf-8").split("\0") if p.endswith(".py"))
    if not files and not errors:
        errors.append("git ls-files 回傳 0 個 tests/ 之 .py（不可能之母體，fail-closed）")
    result = {}
    for rel in files:
        if rel.endswith(("test_probewinsor.py", "probewinsor_helpers.py", "test_probewinsor_batch_resume.py")):
            continue
        try:
            tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as exc:  # fail-closed：列名並以 rc 1 結束
            errors.append(f"{rel}: {type(exc).__name__}: {exc}")
            continue
        scan = Scan()
        scan.visit(tree)
        if scan.r1 or scan.r2:
            result[rel] = {
                "r1_master_off_lines": sorted(set(scan.r1)),
                "r2_symbols": sorted({s for _, s in scan.r2}),
                "r3_hash_literal": bool(scan.r1) and scan.has_hash,
            }
    out.write_text(json.dumps({"files": result, "count": len(result), "scanned": len(files), "errors": errors},
                              ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({"count": len(result), "scanned": len(files), "errors": len(errors),
                      "r1": sum(1 for v in result.values() if v["r1_master_off_lines"]),
                      "r2": sum(1 for v in result.values() if v["r2_symbols"])}, ensure_ascii=False))
    for line in errors:
        print(f"ERROR: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
