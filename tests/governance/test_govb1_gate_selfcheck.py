"""GOVB1 深度自檢閘的機械驗收（2026-08-07，三家裁定 U-7）。

為何存在：`scripts/govb1_selfcheck.sh` 交付時**零呼叫者**（三家獨立命中，
`CODEX-R10-P0-07`／`COMPOSER-R10-P0-01`／`GROK-R10-P0-01`），違反使用者
2026-08-02 治理三原則第 3 條「工具必須自帶強制機制，不准靠紀律和記憶」。
本測試釘住「掛載存在且真的會擋」，使掛載被拿掉時當場轉紅。

⚠️ 本測試**不驗** selfcheck 的檢查內容（那是 `--self-test` 的職責），
只驗**掛載鏈**：gate.sh → govb1_selfcheck.sh → fail-closed。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts" / "gate.sh"
SELFCHECK = REPO / "scripts" / "govb1_selfcheck.sh"
TODO = REPO / "docs" / "GOVB1_INPUT_QUALITY_TODO.md"


def test_selfcheck_script_exists() -> None:
    """runner 本體存在（缺檔即 fail-closed 的前提）。"""
    assert SELFCHECK.is_file(), f"缺 {SELFCHECK}"


def test_gate_mounts_selfcheck() -> None:
    """🔴 掛載鏈存在：gate.sh 必須引用 govb1_selfcheck.sh。

    出生事故：runner 寫完後全 repo 零呼叫者，rc=0 只在主委手動執行時存在。
    """
    src = GATE.read_text(encoding="utf-8")
    assert "govb1_selfcheck.sh" in src, "gate.sh 未掛載 govb1_selfcheck.sh（回到零強制）"
    assert "GOVB1_INPUT_QUALITY_TODO.md" in src, "gate.sh 的掛載未以檔名精確匹配"


def test_mount_is_exact_match_not_glob() -> None:
    """🔴 掛載須**檔名精確匹配**，不得泛化。

    依 U-7：泛化到所有 docs/*TODO*.md 之誤擋率為 97.1%（33/34），違反票 B-23。
    """
    src = GATE.read_text(encoding="utf-8")
    assert "docs/*TODO*.md)" not in src, "掛載被泛化成 glob（誤擋率 97.1%，票 B-23 禁止）"


def test_selfcheck_baseline_green() -> None:
    """基線須全綠——否則掛載會讓所有 impl 派工被擋。"""
    proc = subprocess.run(
        ["bash", str(SELFCHECK)], cwd=str(REPO), capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, f"基線非全綠：\n{proc.stdout}\n{proc.stderr}"


def test_selfcheck_self_test_passes() -> None:
    """🔴 runner 的差分自證須通過——否則 runner 本身可能空轉。

    出生事故：初版自證在基線紅時「突變後也紅」恆真，三條全報 PASS
    但其中一條的 sed 實際失敗、突變根本沒發生。
    """
    proc = subprocess.run(
        ["bash", str(SELFCHECK), "--self-test"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, f"差分自證未過：\n{proc.stdout}\n{proc.stderr}"
    assert "INCONCLUSIVE" not in proc.stdout + proc.stderr, "自證出現 INCONCLUSIVE（基線非綠）"


def test_manifest_count_is_derived_not_handwritten() -> None:
    """檢查 ID 數 == Task 數 × 3 + 5（機器導出，禁手寫）。"""
    man = subprocess.run(
        ["bash", str(SELFCHECK), "--manifest"],
        cwd=str(REPO), capture_output=True, text=True, check=False,
    )
    assert man.returncode == 0
    n_ids = len([ln for ln in man.stdout.splitlines() if ln.strip()])
    n_tasks = sum(1 for ln in TODO.read_text(encoding="utf-8").splitlines()
                  if ln.startswith("### Task "))
    assert n_ids == n_tasks * 3 + 5, f"檢查 ID {n_ids} != Task {n_tasks} × 3 + 5"


def test_every_check_function_writes_its_own_receipt() -> None:
    """🔴 每個 `_chk_*` 必須**自己**寫 receipt（U-6）。

    出生事故：原 dispatcher 代寫 receipt ⇒ `expected == seen` 只證明
    「同一段程式把預期 ID 抄了一份」，**不證明每個檢查真的被呼叫過**
    （`CODEX-R10-P1-06`／`COMPOSER-R10-P1-02`／`GROK-R10-P1-02` 三家獨立命中）。
    """
    import re

    src = SELFCHECK.read_text(encoding="utf-8")
    lines = src.splitlines()
    # `_chk_xxx() {` 後可接註解，故用正則而非 endswith
    pat = re.compile(r"^_chk_[a-z_]+\(\)\s*\{")
    idxs = [i for i, ln in enumerate(lines) if pat.match(ln)]
    assert len(idxs) >= 8, f"檢查函式數異常：{len(idxs)}（{[lines[i].split('(')[0] for i in idxs]}）"

    for i in idxs:
        body_head = "\n".join(lines[i + 1: i + 3])
        assert "_receipt " in body_head, f"{lines[i].split('(')[0]} 未在函式體開頭寫 receipt"


def test_dispatcher_does_not_write_receipts() -> None:
    """🔴 dispatcher **不得**代寫 receipt——代寫即回到循環論證。"""
    src = SELFCHECK.read_text(encoding="utf-8")
    assert 'printf \'%s\\n\' "${id}" >> "${seen_file}"' not in src, (
        "dispatcher 仍在代寫 receipt（U-6 未閉合）"
    )


def test_coverage_boundary_is_always_printed() -> None:
    """🔴 覆蓋邊界宣告須**每次執行都印**（U-2）。

    出生事故：主委把「PASS 44／FAIL 0」報成「TODO 已修好」，兩家證實
    runner 只覆蓋深度紅線子集，多數 oracle 缺陷根本不讀。
    本宣告使「rc=0 ≠ TODO 正確」在每次輸出中都在場，無法被忽略。
    """
    proc = subprocess.run(
        ["bash", str(SELFCHECK)], cwd=str(REPO), capture_output=True, text=True, check=False
    )
    out = proc.stdout + proc.stderr
    assert "覆蓋邊界" in out, "覆蓋邊界宣告未印出（被移除？）"
    assert "不代表" in out, "覆蓋邊界宣告內容被弱化"


def test_gate_rejects_when_selfcheck_red() -> None:
    """🔴 **mutation 自證**：selfcheck 紅時，gate 必須拒發 token。

    以隔離副本把 selfcheck 換成必然失敗的 stub，斷言 gate 非零離開。
    若此測試在 stub 下仍 pass ⇒ 掛載是裝飾性的。
    """
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "always_fail.sh"
        stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        os.chmod(stub, 0o755)

        env = dict(os.environ)
        env["GOVB1_SELFCHECK_OVERRIDE"] = str(stub)

        proc = subprocess.run(
            ["bash", str(GATE), "dispatch",
             "--intent", "probe", "--risk", "low",
             "--facts-asked", "probe", "--review-role", "probe",
             "--template", "n/a: probe",
             "--task-id", "20260807-GOVB1-X-PROBE-R1",
             "--todo", "docs/GOVB1_INPUT_QUALITY_TODO.md"],
            cwd=str(REPO), capture_output=True, text=True, check=False, env=env,
        )
        assert proc.returncode != 0, (
            "selfcheck 為必敗 stub 時 gate 仍放行 ⇒ 掛載是裝飾性的\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
