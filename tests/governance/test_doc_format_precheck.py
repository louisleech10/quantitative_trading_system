"""GOV-DOC-CHECK-AT-WRITE + GOV-DEXT-TEMPLATE-KIND 的驗收與 mutation 自證。

被測物：
  1. scripts/template_check.sh 的新 ``dext`` kind（凍結文件 D 延伸檔）
  2. scripts/brief_conformance_check.sh（從 cx_run.sh 抽出的**唯一實作**）
  3. scripts/doc_format_precheck.sh（PostToolUse hook：產出端檢查）
  4. scripts/gate.sh 對 ``--spec <*.D-NNN.md>`` 的 kind 路由

紀律：
  * 變異一律作用在 **tmp 隔離副本**，絕不改 repo 內 scripts/*.sh。
  * 每個守衛都有對應的 mutation probe：拿掉守衛 → 測試必須轉紅。
  * 不使用恆真斷言；每條斷言都指名具體 rc 或具體字串。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"

# doc_format_precheck 依路徑判型別，故隔離 repo 需有 docs/ 與 handoffs/
_NEEDED = (
    "template_check.sh",
    "brief_conformance_check.sh",
    "doc_format_precheck.sh",
    "coverage_check.sh",
)

_VALID_DEXT = """# 某凍結檔 延伸 D-001

BASE: docs/SOME_SPEC.md @ 9d6e598a1b2c3d4
PREDECESSOR: none
改什麼: 修正一個錨點敘述
為什麼: handoffs/reconcile/xxx/synth.md

## 觸及面宣告
新增: none
覆寫: ## §A 假設與待使用者確認
依賴: none

## 內容

把 §A 第 2 條的路徑敘述改為 registry 登記路徑。

## 戳記
"""


def _iso(tmp_path: Path) -> Path:
    """隔離 repo 副本：只放被測腳本 + 空的 docs/handoffs。"""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "handoffs").mkdir()
    for name in _NEEDED:
        src = SCRIPTS / name
        if src.is_file():
            dst = root / "scripts" / name
            shutil.copy2(src, dst)
            dst.chmod(0o755)
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _mutate(root: Path, name: str, old: str, new: str) -> None:
    """在隔離副本上做逐字取代；找不到目標即 fail（防靜默無動作的假變異）。"""
    p = root / "scripts" / name
    text = p.read_text(encoding="utf-8")
    assert old in text, f"mutation 錨點不存在於 {name}: {old!r}"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# ───────────────────────── dext kind：正例 ─────────────────────────


def test_dext_valid_passes(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "docs" / "X.D-001.md").write_text(_VALID_DEXT, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TEMPLATE PASS (dext)" in r.stdout


def test_dext_real_d001_passes(tmp_path: Path) -> None:
    """對 repo 內真實的 D-001 跑，確保不是只對造出來的樣本有效。"""
    real = REPO_ROOT / "docs" / "P16_COMMITTEE_DEBT_SPEC.D-001.md"
    if not real.is_file():
        pytest.skip("D-001 不存在（已被後續 epic 移除）")
    r = subprocess.run(
        ["bash", "scripts/template_check.sh", "dext", "docs/P16_COMMITTEE_DEBT_SPEC.D-001.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# ───────────────────────── dext kind：反例（逐個必填錨點）─────────────────────────


@pytest.mark.parametrize(
    ("drop", "expect"),
    [
        ("BASE: docs/SOME_SPEC.md @ 9d6e598a1b2c3d4\n", "BASE:"),
        ("PREDECESSOR: none\n", "PREDECESSOR:"),
        ("改什麼: 修正一個錨點敘述\n", "改什麼:"),
        ("為什麼: handoffs/reconcile/xxx/synth.md\n", "為什麼:"),
        ("## 觸及面宣告\n", "## 觸及面宣告"),
        ("新增: none\n", "新增:"),
        ("覆寫: ## §A 假設與待使用者確認\n", "覆寫:"),
        ("依賴: none\n", "依賴:"),
        ("## 戳記\n", "## 戳記"),
    ],
)
def test_dext_missing_anchor_fails(tmp_path: Path, drop: str, expect: str) -> None:
    root = _iso(tmp_path)
    text = _VALID_DEXT.replace(drop, "")
    assert text != _VALID_DEXT, f"樣本裡找不到要刪的片段: {drop!r}"
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "TEMPLATE FAIL (dext)" in r.stdout
    assert expect in r.stdout


def test_dext_blank_touch_declaration_fails(tmp_path: Path) -> None:
    """§2 逐字：『無則寫 none，不得留空』。"""
    root = _iso(tmp_path)
    text = _VALID_DEXT.replace("依賴: none", "依賴:")
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "觸及面宣告欄留空" in r.stdout


def test_dext_base_without_sha_fails(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    text = _VALID_DEXT.replace(
        "BASE: docs/SOME_SPEC.md @ 9d6e598a1b2c3d4", "BASE: docs/SOME_SPEC.md @ HEAD"
    )
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "BASE 缺 commit-sha" in r.stdout


def test_unknown_kind_still_rejected(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "docs" / "X.D-001.md").write_text(_VALID_DEXT, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "bogus", "docs/X.D-001.md")
    assert r.returncode == 1
    assert "kind 必須是 spec|todo|result|dext" in r.stdout


# ─────────────── hollow-3 收窄：只放寬 dext，不得放寬 spec/todo ───────────────


def test_dext_prose_mentioning_verify_not_flagged(tmp_path: Path) -> None:
    """D 延伸檔的散文提到「驗證」二字不算驗證欄（真實誤報：D-001:192）。"""
    root = _iso(tmp_path)
    text = _VALID_DEXT.replace(
        "## 內容\n", "## 內容\n\n- 不改 `gate.sh register-output` 本身的任何驗證\n"
    )
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 0, r.stdout + r.stderr


def test_dext_real_hollow_verify_label_still_flagged(tmp_path: Path) -> None:
    """收窄不是關掉：dext 若把空話寫成行首『驗證』標籤，仍須被抓。"""
    root = _iso(tmp_path)
    text = _VALID_DEXT.replace("## 內容\n", "## 內容\n\n- 驗證：確認正確即可\n")
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "驗證欄不可證偽" in r.stdout


def test_spec_kind_hollow_rule_not_relaxed(tmp_path: Path) -> None:
    """**防迴歸**：spec kind 的 hollow-3 判準（bullet 行含『驗證』）不得被收窄。

    同一段散文在 dext 放行、在 spec 必須照舊被抓——證明收窄綁定 kind，
    不是把檢查整條改弱。
    """
    root = _iso(tmp_path)
    prose = "- 不改 `gate.sh register-output` 本身的任何驗證\n"
    (root / "docs" / "Y_SPEC.md").write_text(
        "# Y\n\n## §A\n\n" + prose, encoding="utf-8"
    )
    r = _run(root, "scripts/template_check.sh", "spec", "docs/Y_SPEC.md")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "驗證欄不可證偽" in r.stdout


# ───────────────────────── doc_format_precheck：路由 ─────────────────────────


def _brief(kind: str, *, compliant: bool) -> str:
    body = f"# probe\n\nbrief-kind: {kind}\n\n"
    if compliant:
        body += (
            "## 範本\n照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行。\n\n"
            "fact-verified: 甲 → 實跑\nassumed: 乙\n"
        )
    return body


def test_precheck_routes_dext(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "docs" / "X.D-002.md").write_text("# 壞\n\n改什麼: 無\n", encoding="utf-8")
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/X.D-002.md")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "判定型別：dext" in r.stderr


def test_precheck_routes_brief_by_content(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "handoffs" / "b.md").write_text(
        _brief("review", compliant=False), encoding="utf-8"
    )
    r = _run(root, "scripts/doc_format_precheck.sh", "handoffs/b.md")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "判定型別：brief" in r.stderr


def test_precheck_compliant_brief_passes(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "handoffs" / "b.md").write_text(
        _brief("review", compliant=True), encoding="utf-8"
    )
    r = _run(root, "scripts/doc_format_precheck.sh", "handoffs/b.md")
    assert r.returncode == 0, r.stdout + r.stderr


def test_precheck_dext_wins_over_spec_naming(tmp_path: Path) -> None:
    """檔名同時像 SPEC 與 D 延伸時，必須判 dext（否則永遠拒發 token 的老 bug 復活）。"""
    root = _iso(tmp_path)
    (root / "docs" / "P16_COMMITTEE_DEBT_SPEC.D-003.md").write_text(
        _VALID_DEXT, encoding="utf-8"
    )
    r = _run(
        root, "scripts/doc_format_precheck.sh", "docs/P16_COMMITTEE_DEBT_SPEC.D-003.md"
    )
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize(
    "rel",
    [
        "docs/PLAIN.md",  # 非 SPEC/TODO/D 延伸
        "handoffs/no-kind.md",  # handoffs 但無 brief-kind
    ],
)
def test_precheck_skips_unrelated(tmp_path: Path, rel: str) -> None:
    """判不出型別就放行——hook 不得亂擋非治理文件。"""
    root = _iso(tmp_path)
    (root / rel).write_text("# 隨便寫\n\n沒有任何治理錨點。\n", encoding="utf-8")
    r = _run(root, "scripts/doc_format_precheck.sh", rel)
    assert r.returncode == 0, r.stdout + r.stderr


def test_precheck_missing_file_is_noop(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/nope.D-001.md")
    assert r.returncode == 0, r.stdout + r.stderr


def test_precheck_hook_mode_reads_stdin_json(tmp_path: Path) -> None:
    """hook 模式：從 PostToolUse 的 JSON 取 tool_input.file_path。"""
    root = _iso(tmp_path)
    target = root / "docs" / "X.D-004.md"
    target.write_text("# 壞\n\n改什麼: 無\n", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    r = subprocess.run(
        ["bash", "scripts/doc_format_precheck.sh"],
        cwd=root,
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 2, r.stdout + r.stderr
    assert "判定型別：dext" in r.stderr


def test_precheck_hook_mode_bad_json_is_noop(tmp_path: Path) -> None:
    """自己解析失敗絕不能擋住使用者工作。"""
    root = _iso(tmp_path)
    r = subprocess.run(
        ["bash", "scripts/doc_format_precheck.sh"],
        cwd=root,
        input="not json at all",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr


# ───────────────────────── brief_conformance_check：--emit 契約 ─────────────────────────


def test_brief_conformance_emits_two_lines(tmp_path: Path) -> None:
    """cx_run.sh 用 sed -n '1p'/'2p' 取值，故第 2 行必須恆存在。"""
    root = _iso(tmp_path)
    (root / "handoffs" / "b.md").write_text(
        _brief("review", compliant=True), encoding="utf-8"
    )
    kv = root / "kv.txt"
    r = _run(
        root, "scripts/brief_conformance_check.sh", "handoffs/b.md", "--emit", str(kv)
    )
    assert r.returncode == 0, r.stdout + r.stderr
    lines = kv.read_text(encoding="utf-8").split("\n")
    assert lines[0] == "review"
    assert lines[1] == ""


def test_brief_conformance_emits_stamp_target(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "handoffs" / "tgt.md").write_text("## 戳記\n", encoding="utf-8")
    (root / "handoffs" / "b.md").write_text(
        "# p\n\nbrief-kind: stamp\nstamp-target: handoffs/tgt.md\n", encoding="utf-8"
    )
    kv = root / "kv.txt"
    r = _run(
        root, "scripts/brief_conformance_check.sh", "handoffs/b.md", "--emit", str(kv)
    )
    assert r.returncode == 0, r.stdout + r.stderr
    lines = kv.read_text(encoding="utf-8").split("\n")
    assert lines[0] == "stamp"
    assert lines[1] == "handoffs/tgt.md"


def test_brief_conformance_no_emit_file_on_failure(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "handoffs" / "b.md").write_text(
        _brief("review", compliant=False), encoding="utf-8"
    )
    kv = root / "kv.txt"
    r = _run(
        root, "scripts/brief_conformance_check.sh", "handoffs/b.md", "--emit", str(kv)
    )
    assert r.returncode == 2
    assert not kv.exists(), "檢查失敗時不得寫出 kv 檔（呼叫端會讀到殘值）"


def test_brief_conformance_stamp_target_traversal_rejected(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    (root / "handoffs" / "b.md").write_text(
        "# p\n\nbrief-kind: stamp\nstamp-target: handoffs/../../etc/passwd\n",
        encoding="utf-8",
    )
    r = _run(root, "scripts/brief_conformance_check.sh", "handoffs/b.md")
    assert r.returncode == 2
    assert "不得含 .." in r.stderr


# ───────────────────────── mutation probes（拿掉守衛 → 轉紅）─────────────────────────


def test_mutation_dext_anchor_check_removed_turns_red(tmp_path: Path) -> None:
    """把 dext 的 `## 戳記` 錨點檢查拿掉 → 缺戳記區的檔會被誤判合規。"""
    root = _iso(tmp_path)
    _mutate(
        root,
        "template_check.sh",
        'need "## 戳記" "§2：GROK-R7-P1-01',
        'true "## 戳記" "MUTATED',
    )
    text = _VALID_DEXT.replace("## 戳記\n", "")
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 0, "變異後應誤放行——若仍為 1 表示這條探針沒真的關掉守衛"


def test_mutation_blank_touch_check_removed_turns_red(tmp_path: Path) -> None:
    root = _iso(tmp_path)
    _mutate(
        root,
        "template_check.sh",
        'if [ -n "${dext_blank}" ]; then',
        "if false; then  # MUTATED",
    )
    text = _VALID_DEXT.replace("依賴: none", "依賴:")
    (root / "docs" / "X.D-001.md").write_text(text, encoding="utf-8")
    r = _run(root, "scripts/template_check.sh", "dext", "docs/X.D-001.md")
    assert r.returncode == 0, "變異後應誤放行"


def test_mutation_hollow3_narrowing_leaks_to_spec_turns_red(tmp_path: Path) -> None:
    """若把收窄誤寫成無條件（所有 kind 都收窄）→ spec 的既有保護被弱化。

    這條探針守的是「不得放寬既有 kind」這個承諾本身。
    """
    root = _iso(tmp_path)
    _mutate(
        root,
        "template_check.sh",
        'if [ "${kind}" = "dext" ]; then\n',
        "if true; then  # MUTATED: narrowing leaks to all kinds\n",
    )
    (root / "docs" / "Y_SPEC.md").write_text(
        "# Y\n\n## §A\n\n- 不改 `gate.sh register-output` 本身的任何驗證\n",
        encoding="utf-8",
    )
    r = _run(root, "scripts/template_check.sh", "spec", "docs/Y_SPEC.md")
    # 這份最小 spec 本來就缺一堆錨點，rc 必為 1，**不能拿 rc 當判準**（會恆真）。
    # 判準是 hollow-3 那條訊息在不在：未變異時在（見 test_spec_kind_hollow_rule_not_relaxed），
    # 變異後應消失 → 證明收窄確實綁定 kind，而非整條放寬。
    assert (
        "驗證欄不可證偽" not in r.stdout
    ), "變異後 spec 仍被 hollow-3 抓到——表示這條探針沒真的把收窄洩漏出去"


def test_mutation_precheck_routing_removed_turns_red(tmp_path: Path) -> None:
    """拿掉 dext 路由 → D 延伸檔會掉回 spec kind，回到『永遠拒發 token』的老 bug。"""
    root = _iso(tmp_path)
    # 必須**整條刪掉**指派 dext 的那行：case 只跑第一個命中的 arm，
    # 若只把值改成空字串，控制流不會落到後面的 spec arm（第一版探針就是這樣寫錯的）。
    # 路由改為 basename 判定後（CODEX-R1-P2-04），錨點是內層 case 的指派行。
    _mutate(
        root,
        "doc_format_precheck.sh",
        '      *.D-[0-9][0-9][0-9].md) kind="dext" ;;\n',
        "      # MUTATED: dext assignment removed\n",
    )
    (root / "docs" / "P_SPEC.D-005.md").write_text(_VALID_DEXT, encoding="utf-8")
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/P_SPEC.D-005.md")
    assert r.returncode == 2, "變異後應改判 spec 並失敗"
    assert "判定型別：spec" in r.stderr


# ─────────── CODEX-R1-P2-04：glob 跨 `/` 導致巢狀路徑被誤判 dext ───────────


def test_nested_path_not_routed_to_dext(tmp_path: Path) -> None:
    """`docs/sub/x.D-001.md` 不得判 dext。

    凍結程序 §2 規定的是 `docs/<原檔 basename>.D-<NNN>.md`＝docs 正下方一層。
    shell 的 `*` 會跨 `/`，第一版樣式 `docs/*.D-NNN.md` 會誤命中巢狀路徑，
    後果是拿較窄的 dext 檢查取代該跑的 spec 檢查。
    """
    root = _iso(tmp_path)
    (root / "docs" / "sub").mkdir()
    # 內容是合法 dext；若被誤判 dext 就會 rc=0，判 spec 才會因缺 SPEC 錨點而 rc=2
    (root / "docs" / "sub" / "nested_SPEC.D-001.md").write_text(
        _VALID_DEXT, encoding="utf-8"
    )
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/sub/nested_SPEC.D-001.md")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "判定型別：spec" in r.stderr, "巢狀路徑被誤判成 dext"


def test_top_level_dext_still_routed(tmp_path: Path) -> None:
    """收窄不得誤傷正常情形：docs 正下方的 D 延伸檔仍須判 dext。"""
    root = _iso(tmp_path)
    (root / "docs" / "A_SPEC.D-001.md").write_text(_VALID_DEXT, encoding="utf-8")
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/A_SPEC.D-001.md")
    assert r.returncode == 0, r.stdout + r.stderr


def test_mutation_nested_glob_restored_turns_red(tmp_path: Path) -> None:
    """把樣式改回會跨 `/` 的版本 → 巢狀路徑又被誤判 dext。"""
    root = _iso(tmp_path)
    _mutate(
        root,
        "doc_format_precheck.sh",
        '  docs/*/*) : ;;   # docs 子目錄不在 §2 規範內，交後面的一般規則\n',
        "  docs/*/*) kind=\"dext\" ;;  # MUTATED: glob 跨 / 回歸\n",
    )
    (root / "docs" / "sub").mkdir()
    (root / "docs" / "sub" / "nested_SPEC.D-001.md").write_text(
        _VALID_DEXT, encoding="utf-8"
    )
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/sub/nested_SPEC.D-001.md")
    assert r.returncode == 0, "變異後巢狀檔應被誤判 dext 而放行"


def test_mutation_precheck_exit_code_swallowed_turns_red(tmp_path: Path) -> None:
    """把 rc 吞掉 → hook 永遠不報，等於沒掛。"""
    root = _iso(tmp_path)
    _mutate(root, "doc_format_precheck.sh", "exit 2\n", "exit 0\n  # MUTATED\n")
    (root / "docs" / "X.D-006.md").write_text("# 壞\n\n改什麼: 無\n", encoding="utf-8")
    r = _run(root, "scripts/doc_format_precheck.sh", "docs/X.D-006.md")
    assert r.returncode == 0, "變異後應誤放行"
