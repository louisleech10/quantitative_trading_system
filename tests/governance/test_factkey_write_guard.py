"""factkey_write_guard.sh — fact-key 機制之產出端檢查（GOV-FACTKEY-CHECK-AT-WRITE）。

使用者 2026-08-13 逐字：「所有在產出完成前沒辦法擋的都等於沒意義」。
`票 B-25` 三段交付後檢查全在 pre-push（消費端），違反使用者 2026-08-02 定死的
治理三原則第 3 條「檢查點放產出端非消費端」。本守衛是第 ① 層。

🔴 本檔特別驗證**強制機制存在性**（原則第 3 條：提案未答「怎麼被強制執行」不算完成）——
   `test_guard_is_wired_into_posttooluse` 直接讀 settings.json，掛載被移除即轉紅。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "scripts" / "factkey_write_guard.sh"
GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
SETTINGS = REPO / ".claude" / "settings.json"

_MIN_SCHEMA = {
    "status_enum": ["✅"],
    "status_keys": ["k"],
    "status_scope": ["docs/"],
    "status_scope_grandfathered": ["docs/__none__.md"],
}
_EO = "docs/GOVERNANCE_EXECUTION_ORDER.md"
_FIX = "tests/governance/fixtures/govb1"


def _mkrepo(tmp_path: Path, *, registry: dict | None = None, drift_same: bool = False) -> Path:
    """建一棵最小假 repo：scripts/ ＋ 宿主檔 ＋ 兩個 fixture。

    🔴 守衛的 REPO_ROOT 由腳本自身位置導出（SCRIPT_DIR/..），故必須複製 scripts/ 進來，
    不能只指環境變數 —— 這也是守衛與 `gen_fact_key_blocks.sh` 的刻意差異。
    """
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GUARD, root / "scripts" / GUARD.name)
    shutil.copy2(GEN, root / "scripts" / GEN.name)
    reg = registry if registry is not None else {
        "_schema": dict(_MIN_SCHEMA),
        "k": {"target": "docs/t.md", "rows": [["010", "ZZ-01", "x"]]},
    }
    (root / "scripts" / "fact_keys.json").write_text(
        json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for key, val in reg.items():
        if key == "_schema":
            continue
        tgts = val["target"]
        for t in ([tgts] if isinstance(tgts, str) else tgts):
            p = root / t
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"前言\n<!-- BEGIN GENERATED: {key} -->\n"
                         f"<!-- END GENERATED: {key} -->\n", encoding="utf-8")
    # 兩個 fixture 的對照檔（守衛的鑑別力守衛只看這一對）
    for sub in ("factkey_clean", "factkey_drifted"):
        p = root / _FIX / sub / "docs" / "GOVERNANCE_EXECUTION_ORDER.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("| 140 | 批 0.9 | B-37 |\n", encoding="utf-8")
    if not drift_same:
        (root / _FIX / "factkey_drifted" / "docs" / "GOVERNANCE_EXECUTION_ORDER.md").write_text(
            "| 140 | 批 0.9 | B-99（竄改） |\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    # 生成區塊落地，使基準為綠
    subprocess.run(["bash", str(root / "scripts" / GEN.name), "--write"],
                   cwd=str(root), capture_output=True)
    return root


def _run(root: Path, arg: str | None = None, *, stdin: str | None = None):
    cmd = ["bash", str(root / "scripts" / GUARD.name)]
    if arg is not None:
        cmd.append(arg)
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                          input=stdin if stdin is not None else "")


def test_guard_exists_and_executable():
    assert GUARD.is_file(), f"缺守衛 {GUARD}"
    assert os.access(GUARD, os.X_OK), "守衛須可執行"


def test_guard_is_wired_into_posttooluse():
    """🔴 強制機制存在性（使用者定死之治理三原則第 3 條）。

    工具寫出來不算完成，**要有強制使用機制**。本測試直接讀 settings.json：
    掛載被移除、或 matcher 不再涵蓋 Edit|Write，本條即轉紅。
    """
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {}).get("PostToolUse", [])
    hit = [
        entry for entry in hooks
        if "Edit" in (entry.get("matcher") or "") and "Write" in (entry.get("matcher") or "")
        and any(GUARD.name in (h.get("command") or "") for h in entry.get("hooks", []))
    ]
    assert hit, (
        f"{GUARD.name} 未掛在 settings.json 的 PostToolUse(Edit|Write) ⇒ "
        "檢查點退回消費端，本機制等同不存在"
    )


def test_clean_tree_is_rc_zero(tmp_path):
    root = _mkrepo(tmp_path)
    r = _run(root, "scripts/fact_keys.json")
    assert r.returncode == 0, r.stderr


def test_unmanaged_file_is_not_checked(tmp_path):
    """範圍封閉：不受管的檔不觸發，即使樹上同時有問題。"""
    root = _mkrepo(tmp_path, drift_same=True)      # 樹上已有 fixture 問題
    r = _run(root, "README.md")
    assert r.returncode == 0, f"不受管檔觸發了檢查 ⇒ 範圍不封閉\n{r.stderr}"


def test_registry_drift_is_caught_at_write_time(tmp_path):
    """改了註冊表沒跑 --write ⇒ 當場報，不必等到 push。"""
    root = _mkrepo(tmp_path)
    reg_path = root / "scripts" / "fact_keys.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg["k"]["rows"][0][2] = "改過但沒重生成"
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = _run(root, "scripts/fact_keys.json")
    assert r.returncode == 2, f"漂移未被產出端抓到\n{r.stdout}"
    assert "--write" in r.stderr, f"訊息未給修法一行\n{r.stderr}"


def test_fixture_discriminating_power_loss_is_caught(tmp_path):
    """🔴 本 session 實際發生 5 次：`--write` 把 drifted 的竄改列洗回與 clean 相同。

    正反對照因此變成兩個 clean，drifted 那條恆綠（空心）而無人察覺。
    """
    root = _mkrepo(tmp_path, drift_same=True)
    r = _run(root, "scripts/fact_keys.json")
    assert r.returncode == 2, f"fixture 鑑別力失效未被抓到\n{r.stdout}"
    assert "鑑別力已失" in r.stderr, r.stderr


def test_managed_set_is_derived_from_registry_not_hardcoded(tmp_path):
    """受管集合由註冊表導出：新增 target 自動納入，不需改守衛。

    寫死清單就是下一個過期副本 —— 本 epic 已因此吃虧多次。
    """
    reg = {
        "_schema": dict(_MIN_SCHEMA),
        "k": {"target": ["docs/t.md", "docs/newly_added.md"],
              "rows": [["010", "ZZ-01", "x"]]},
    }
    root = _mkrepo(tmp_path, registry=reg)
    # 破壞新宿主的區塊，使 --check 轉紅
    (root / "docs" / "newly_added.md").write_text("沒有區塊\n", encoding="utf-8")
    r = _run(root, "docs/newly_added.md")
    assert r.returncode == 2, (
        "新登記的 target 未被守衛認定為受管 ⇒ 受管集合可能是寫死的\n" + r.stdout
    )


def test_hook_mode_reads_file_path_from_stdin(tmp_path):
    """hook 模式：PostToolUse 以 stdin 餵 JSON。"""
    root = _mkrepo(tmp_path, drift_same=True)
    payload = json.dumps({"tool_input": {"file_path": str(root / "scripts" / "fact_keys.json")}})
    r = _run(root, stdin=payload)
    assert r.returncode == 2, f"hook 模式未取到 file_path\n{r.stdout}\n{r.stderr}"


def test_unparseable_stdin_is_silently_allowed(tmp_path):
    """🔴 具名 fail-open（刻意，邊界 4）：hook 不得因自己解析失敗而擋住工作。

    代價由第 ②③ 層（gov_check 第 3 段、派工閘）承接，那兩層是 fail-closed。
    若哪天改成 fail-closed，本測試會轉紅 —— 屆時請同步更新守衛檔頭的邊界 4。
    """
    root = _mkrepo(tmp_path, drift_same=True)
    r = _run(root, stdin="這不是 JSON")
    assert r.returncode == 0, (
        "hook 對無法解析的輸入改成擋下了 ⇒ 邊界 4 的宣稱過期，請更新守衛檔頭\n" + r.stderr
    )


def test_path_outside_repo_is_ignored(tmp_path):
    root = _mkrepo(tmp_path, drift_same=True)
    r = _run(root, "/etc/hosts")
    assert r.returncode == 0, f"repo 外路徑不應觸發\n{r.stderr}"


def test_mutation_removing_fixture_guard_lets_it_through(tmp_path):
    """反面實證：拿掉 fixture 鑑別力守衛後，CX 就通過 ⇒ 證明該條不是空心格。"""
    root = _mkrepo(tmp_path, drift_same=True)
    p = root / "scripts" / GUARD.name
    src = p.read_text(encoding="utf-8")
    anchor = 'if [ -f "${_clean}" ] && [ -f "${_drift}" ] && cmp -s "${_clean}" "${_drift}"; then'
    assert anchor in src, "mutation 錨點不存在（守衛已改寫？）"
    p.write_text(src.replace(anchor, "if false; then", 1), encoding="utf-8")
    r = _run(root, "scripts/fact_keys.json")
    assert r.returncode == 0, f"拿掉 fixture 守衛後仍紅 ⇒ 這條 mutation 是空心的\n{r.stderr}"
