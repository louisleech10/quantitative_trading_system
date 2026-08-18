"""Task 2.4 驗證：策略層 wiring 閘（AST；W1..W4）常駐＋六條 mutation（各 rc=1）＋ rc=2 邊界。"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
SH = REPO / "scripts" / "strategy_wiring_check.sh"
PY = REPO / "scripts" / "strategy_wiring_check.py"
CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "strategy_validation_contract.json"
PKG = REPO / "momentum" / "Analysis" / "strategy_validation"


def _run(*args):
    return subprocess.run([sys.executable, str(PY), *args], capture_output=True, text=True, check=False, timeout=120)


def _copy_pkg(tmp_path):
    dst = tmp_path / "pkg"
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def _copy_contract(tmp_path, mutate=None):
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if mutate:
        mutate(payload)
    dst = tmp_path / "contract.json"
    dst.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return dst


def test_sh_wrapper_and_default_paths_pass():
    """常駐：`bash scripts/strategy_wiring_check.sh` rc=0；`bash -n` rc=0。"""
    proc = subprocess.run(["bash", "-n", str(SH)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(["bash", str(SH)], capture_output=True, text=True, check=False, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "✓ W1..W4" in proc.stdout


def test_tmp_copies_pass_baseline(tmp_path):
    pkg = _copy_pkg(tmp_path)
    c = _copy_contract(tmp_path)
    proc = _run("--contract", str(c), "--pkg", str(pkg))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_mutation_1_contract_adds_unassembled_section(tmp_path):
    """① tmp 契約加未被組裝之 section ⇒ rc=1（W1）。"""
    pkg = _copy_pkg(tmp_path)

    def _m(p):
        p["report_sections"]["ghost"] = {"required_keys": ["status"], "types": {"status": ["str"]}, "additional_properties": False}

    c = _copy_contract(tmp_path, _m)
    proc = _run("--contract", str(c), "--pkg", str(pkg))
    assert proc.returncode == 1 and "W1" in proc.stdout and "ghost" in proc.stdout


def test_mutation_2_invented_reason_keyword(tmp_path):
    """② tmp pkg 檔加 `reason="invented_x"` ⇒ rc=1（W3）。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text('def f(**k):\n    return k\n\nx = f(reason="invented_x")\n', encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "invented_x" in proc.stdout


def test_mutation_3_invented_reason_dict_form(tmp_path):
    """③ `{"reason": "invented_y"}` dict 形 ⇒ rc=1（W3 之 regex 版漏洞回歸鎖）。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text('payload = {"status": "ok", "reason": "invented_y"}\n', encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "invented_y" in proc.stdout


def test_mutation_4_section_only_in_docstring_and_comment(tmp_path):
    """④ tmp report.py 把 `pbo` 節名只寫進註解／docstring 而不組裝 ⇒ rc=1（W1 假綠回歸鎖）。"""
    pkg = _copy_pkg(tmp_path)
    src = (pkg / "report.py").read_text(encoding="utf-8")
    assert '"pbo": {' in src
    mutated = src.replace('"pbo": {', '"pbo_renamed": {', 1)
    mutated = mutated.replace("def build_validation_section(", '# "pbo" 節在此註解與下方 docstring 出現\ndef build_validation_section(', 1)
    mutated = mutated.replace('    """組五節＋降級旗標', '    """"pbo" "pbo" 組五節＋降級旗標', 1)
    (pkg / "report.py").write_text(mutated, encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "W1" in proc.stdout and "pbo" in proc.stdout


def test_mutation_5_dynamic_reason_fstring_is_unresolved(tmp_path):
    """⑤ `reason=f"x_{i}"`（動態）⇒ rc=1（[unresolved] fail-closed）。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text('def f(**k):\n    return k\n\ni = 3\nx = f(reason=f"x_{i}")\n', encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "unresolved" in proc.stdout


def test_mutation_5b_variable_holding_fstring_is_unresolved(tmp_path):
    """⑤b `tmp = f"..."; reason=tmp`（經變數之動態值）亦 unresolved。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text('def f(**k):\n    return k\n\ni = 3\ntmp = f"x_{i}"\nx = f(reason=tmp)\n', encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "unresolved" in proc.stdout


def test_mutation_6_dead_branch_does_not_count(tmp_path):
    """⑥ A1-17 死分支假綠回歸鎖：`out={四節}`＋`if False: out["pbo"]={…}`＋`return out` ⇒ rc=1；eligibility 九鍵寫在 `if False:` 內亦 rc=1。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "report.py").write_text(
        'WARNING_TEXT_KEY = "strategy_validation.downgraded"\n'
        "def build_validation_section(*, eligibility, dsr, pbo, provenance):\n"
        '    out = {"eligibility": {}, "min_btl": {}, "dsr": {}, "provenance": {}}\n'
        "    if False:\n"
        '        out["pbo"] = {"status": "ok"}\n'
        '        out["eligibility"] = {"eligible": None, "required_years_upper_bound": None, "available_years": None,\n'
        '                              "trials_budget": None, "trials_used": None, "target_sharpe": None,\n'
        '                              "n_source": "ledger", "display_downgrade": True, "warning_text_key": ""}\n'
        "    return out\n",
        encoding="utf-8",
    )
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1
    assert "W1" in proc.stdout and "pbo" in proc.stdout
    assert "W4" in proc.stdout


def test_dead_enum_reason_is_red(tmp_path):
    """W2：契約 reasons 多一值而 pkg 無該 Constant ⇒ rc=1（死枚舉）。"""
    pkg = _copy_pkg(tmp_path)

    def _m(p):
        p["reasons"].append("never_emitted")
        p["reason_conditions"]["never_emitted"] = {"condition": "x", "assertion_ref": "x"}

    proc = _run("--contract", str(_copy_contract(tmp_path, _m)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "never_emitted" in proc.stdout


def test_rc2_boundaries(tmp_path):
    """缺契約／缺 report.py／語法錯／無目標函式 ⇒ rc=2。"""
    pkg = _copy_pkg(tmp_path)
    c = _copy_contract(tmp_path)
    assert _run("--contract", str(tmp_path / "nope.json"), "--pkg", str(pkg)).returncode == 2
    (pkg / "report.py").unlink()
    assert _run("--contract", str(c), "--pkg", str(pkg)).returncode == 2
    (pkg / "report.py").write_text("def build_validation_section(:\n", encoding="utf-8")
    assert _run("--contract", str(c), "--pkg", str(pkg)).returncode == 2
    (pkg / "report.py").write_text("def other():\n    return {}\n", encoding="utf-8")
    assert _run("--contract", str(c), "--pkg", str(pkg)).returncode == 2


def test_empty_reasons_is_rc1(tmp_path):
    """邊界③ 契約 reasons 空 ⇒ rc=1。"""
    pkg = _copy_pkg(tmp_path)

    def _m(p):
        p["reasons"] = []
        p["reason_conditions"] = {}

    proc = _run("--contract", str(_copy_contract(tmp_path, _m)), "--pkg", str(pkg))
    assert proc.returncode == 1


# ── B4 review N1（A1-24）：passthrough 白名單收窄之回歸鎖 ─────────────────────


@pytest.mark.parametrize(
    "snippet",
    [
        'data = {"not_reason": "invented_v"}\nx = f(reason=data["not_reason"])\n',  # Subscript 非 "reason" 鍵
        'class O:\n    other = "invented_w"\nx = f(reason=O().other)\n',  # Attribute 非 .reason
        'd = {"other": "n_unknown"}\nx = f(reason=d.get("other", "n_unknown"))\n',  # .get 首參數非 "reason"
        '_R = "n_unknown"\ndef g(i):\n    _R = f"x_{i}"\n    return f(reason=_R)\n',  # 區域 f-string 遮蔽同名頂層常數
        'def g(v):\n    reason = v + "_x"\n    return f(reason=reason)\n',  # BinOp
    ],
)
def test_mutation_n1_non_whitelisted_passthrough_is_unresolved(tmp_path, snippet):
    """grok／codex R18 反例：非白名單之屬性／字典鍵／`.get` 首參數／區域遮蔽／BinOp ⇒ [unresolved] rc=1。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text("def f(**k):\n    return k\n\n" + snippet, encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "unresolved" in proc.stdout, proc.stdout


def test_whitelisted_passthrough_forms_pass(tmp_path):
    """白名單形態（`x.reason`／`x["reason"]`／`.get("reason", "")`／IfExp／參數／模組常數）⇒ rc=0。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text(
        "def f(**k):\n    return k\n\n"
        '_R = "n_unknown"\n'
        "def g(obj, d, flag, reason):\n"
        '    a = f(reason=obj.reason)\n'
        '    b = f(reason=d["reason"])\n'
        '    c = f(reason=d.get("reason", ""))\n'
        '    e = f(reason=_R if flag else "")\n'
        "    h = f(reason=reason)\n"
        "    return a, b, c, e, h\n",
        encoding="utf-8",
    )
    proc = _run("--contract", str(_copy_contract(tmp_path)), "--pkg", str(pkg))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_mutation_n1_dead_enum_via_unused_constant_or_docstring_is_red(tmp_path):
    """codex R18 P2-06：契約多一 reason，pkg 只以**未引用常數**／docstring 出現 ⇒ 仍為死枚舉 rc=1（W2）。"""
    pkg = _copy_pkg(tmp_path)
    (pkg / "extra_mod.py").write_text('"""docstring mentions ghost_reason"""\nUNUSED = "ghost_reason"\n', encoding="utf-8")

    def _m(p):
        p["reasons"].append("ghost_reason")
        p["reason_conditions"]["ghost_reason"] = {"condition": "x", "assertion_ref": "x"}

    proc = _run("--contract", str(_copy_contract(tmp_path, _m)), "--pkg", str(pkg))
    assert proc.returncode == 1 and "ghost_reason" in proc.stdout and "W2" in proc.stdout
    # 對照：被引用之模組常數即算接線
    (pkg / "extra_mod.py").write_text('def f(**k):\n    return k\n\n_G = "ghost_reason"\nx = f(reason=_G)\n', encoding="utf-8")
    proc = _run("--contract", str(_copy_contract(tmp_path, _m)), "--pkg", str(pkg))
    assert proc.returncode == 0, proc.stdout
