"""票 B-49 閉合證據 — 六格獨立 selector ＋ 隔離 runner（SPEC Task 2.3 / 3.1）。

每一格由**自己的** rc／passed／skipped 獨立判定，對應票文條件 1／2-①②③／3。
🔴 不得以任一格之 receipt 兼充另一格；不得在主工作樹跑；不得以整檔 `exit 0` 取代具名 selector。

隔離 runner 之 fail-closed 判準（`CODEX-R1-P1-03`；缺一即紅）：
  ① `scripts/` **實體 copy**，setup 後斷言不是 symlink
  ② env 最小集＝`{PATH, HOME, LANG=C.UTF-8}`，其餘**清空**（非繼承）
  ③ `-p no:cacheprovider` ＋明確 `cwd` ＋逾時上限
  ④ 子程序前後對主 repo 做 snapshot diff，**不相等即紅**
  ⑤ 上述任一步失敗 ⇒ **直接紅**，不得被子程序自身的 `rc == 0` 掩蓋
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tests.governance import _role_pin  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STAMP_FILE = "tests/governance/test_stamp_taskid_inject.py"
V12_FN = "test_v12_non_stamp_kinds_no_stamp_target_ok"
_TIMEOUT = 600

# 🔴 外部字面集合：2-② 之判準寫字面 `passed == 3`，**不得**寫 `len(review_families)`
# （自我參照 ⇒ 名冊縮成一家時判準跟著縮，恆真）。
_EXPECTED_CLI_FAMILIES = ("codex", "composer", "grok")


# ── 隔離 runner ──────────────────────────────────────────────────────


# 🔴 snapshot 之 ignored 掃描要排除的重目錄（資料／依賴，非 repo 產物）。
# 具名殘留：子程序若只寫這幾個目錄，本 snapshot 看不到。它們不是治理程式碼的產出面。
_SNAPSHOT_EXCLUDE = (
    ":!data_cache",
    ":!venv",
    ":!node_modules",
    ":!frontend/node_modules",
    ":!.git",
)


def _repo_snapshot() -> str:
    """主 repo 的工作區快照（供 ④ 前後比對）。

    〔`CODEX-R2-P1-03`〕原本只取 `git status --porcelain`：**看不到 `.gitignore` 之下的
    副作用**（`data_cache/`、`.pytest_cache/` …）⇒ 子程序寫 ignored path 時前後相同，
    被判定為「沒動到主 repo」。改為同時涵蓋 tracked／untracked／ignored，
    重目錄以 pathspec 具名排除（見 `_SNAPSHOT_EXCLUDE`）。
    取不到一律 fail-closed。
    """
    p = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all",
         "--ignored=traditional", "--", *_SNAPSHOT_EXCLUDE],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, f"snapshot 取不到（fail-closed）：{p.stderr}"
    return p.stdout


def _make_iso(tmp_path: Path) -> Path:
    """實體複製受測子集到 tmp（**禁 symlink**）。"""
    dst = tmp_path / "iso"
    dst.mkdir(parents=True, exist_ok=True)
    for rel in ("scripts", "templates"):
        shutil.copytree(REPO / rel, dst / rel, symlinks=False, dirs_exist_ok=True)
    (dst / "tests").mkdir(exist_ok=True)
    shutil.copytree(
        REPO / "tests" / "governance",
        dst / "tests" / "governance",
        symlinks=False,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("fixtures", "__pycache__", ".pytest_cache"),
    )
    for f in ("conftest.py", "pytest.ini"):
        if (REPO / f).is_file():
            shutil.copy2(REPO / f, dst / f)
    for pkg in (dst / "tests", dst / "tests" / "governance"):
        init = pkg / "__init__.py"
        if (REPO / init.relative_to(dst)).is_file() and not init.is_file():
            shutil.copy2(REPO / init.relative_to(dst), init)
    (dst / "handoffs").mkdir(exist_ok=True)
    (dst / "docs").mkdir(exist_ok=True)
    # 🔴 隔離副本必須是 git repo：巢狀執行時（閉合證據 → 隔離副本 → 副本內再開副本）
    #    副本內的 `_repo_snapshot()` 會對副本根跑 `git status`，非 repo 即 fail-closed
    #    ⇒ 關票路徑不可達。此為 review r2 反向驗證實測到的第二個「無可達終態」。
    if not (dst / ".git").exists():
        init = subprocess.run(
            ["git", "init", "-q"], cwd=str(dst), capture_output=True, text=True, check=False
        )
        assert init.returncode == 0, f"隔離副本 git init 失敗（fail-closed）：{init.stderr}"
    _assert_physical_copy(dst)
    return dst


def _assert_physical_copy(dst: Path) -> None:
    """runner 判準①：`scripts/` 須為**實體 copy**，不得是 symlink。

    獨立成函式，好讓 mutation ⑭ 直接呼叫**同一個**守衛——
    在測試裡另寫一份 assert 再用 `pytest.raises` 包住是自證循環，不承重。
    """
    assert not (dst / "scripts").is_symlink(), f"隔離失敗：scripts 是 symlink（{dst}）"
    assert (dst / "scripts").is_dir(), f"隔離副本缺 scripts 目錄（{dst}）"
    assert (dst / "scripts" / "cx_run.sh").is_file(), "隔離副本缺 cx_run.sh"


def _run_iso(iso: Path, selector: str) -> dict[str, int | str]:
    """在隔離副本跑單一 selector；回傳 rc／passed／skipped／failed／輸出。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(iso)),
        "LANG": "C.UTF-8",
    }
    before = _repo_snapshot()
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", selector, "-q", "--tb=short",
             "-p", "no:cacheprovider"],
            cwd=str(iso),
            env=env,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:  # ③ 逾時 ⇒ 直接紅
        raise AssertionError(f"隔離子程序逾時 {_TIMEOUT}s：{selector}") from exc
    after = _repo_snapshot()
    # ④ 主 repo 不得被子程序動到
    assert before == after, (
        f"隔離子程序改動了主 repo（selector={selector}）\n"
        f"before={before!r}\nafter={after!r}"
    )
    out = p.stdout + p.stderr

    def _n(word: str) -> int:
        m = re.search(rf"(\d+) {word}", out)
        return int(m.group(1)) if m else 0

    return {
        "rc": p.returncode,
        "passed": _n("passed"),
        "skipped": _n("skipped"),
        "failed": _n("failed"),
        "error": _n("error"),
        "out": out,
    }


# ── 票文條件 1-a：V12 本體不得有 skip 逃生口 ─────────────────────────


def _fn_source(path: Path, fn: str) -> str:
    """取函式原始碼片段，**含其上方的 decorator 行**。"""
    src = path.read_text(encoding="utf-8")
    m = re.search(rf"^((?:@[^\n]*\n)*)def {re.escape(fn)}\(", src, re.M)
    assert m, f"{path.name} 找不到 {fn}"
    start = m.start()
    tail = src[m.end():]
    end = re.search(r"\n(?=@|def |\Z)", tail)
    return src[start : m.end() + (end.start() if end else len(tail))]


def test_v12_body_has_no_skip_escape() -> None:
    """1-a：V12 函式片段（**含 decorator**）不得出現不分大小寫之 `skip`。

    🔴 **禁字面 `pytest.skip` 子串掃描**——`pytest.skip` 可被 import 改名、
    可寫成 `getattr(pytest, "sk" + "ip")`。改用封閉規則：整段原始碼不得出現 `skip`
    （不分大小寫）。這條規則是**封閉可導出**的，非黑名單列舉。
    """
    seg = _fn_source(REPO / STAMP_FILE, V12_FN)
    assert "skip" not in seg.lower(), (
        f"{V12_FN} 仍含 skip 逃生口 ⇒ 票 B-49 條件 1 未達成：\n{seg[:400]}"
    )


# ── 票文條件 1-b：V12 四個 kind 逐一 visit，零 skip ──────────────────


def test_v12_four_kinds_all_visited(tmp_path: Path) -> None:
    """1-b：`passed == 4` 且 `skipped == 0`（parametrize ⇒ per-kind visit receipt）。

    🔴 原寫法是 `for kind in (...)` 單一測試——**跑幾個 kind 從 receipt 看不出來**，
    中途 skip 也只算一次 skipped。參數化後每個 kind 各一格。
    """
    iso = _make_iso(tmp_path)
    r = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
    assert r["rc"] == 0, f"1-b 基線應綠：\n{r['out'][-3000:]}"
    assert r["passed"] == 4, f"期望 4 格 per-kind receipt，得 {r['passed']}\n{r['out'][-2000:]}"
    assert r["skipped"] == 0, f"1-b 不得有 skip，得 {r['skipped']}"


# ── 票文條件 2-①：invalid implementer 必須轉紅（非靜默 skip）────────


def test_stamp_path_invalid_implementer_turns_red(tmp_path: Path) -> None:
    """2-①：base `rc == 0`；名冊給不出 CLI 家族時 `rc != 0` 且 `skipped == 0`。

    🔴 **變異目標與 SPEC 原文不同，理由須逐字保留**：SPEC 寫「變異須落在 stamp path
    的 invalid-implementer 分支」。修法之後**那個分支已經不存在**——那正是本票要達成的
    結果（沙箱名冊釘定 ⇒ 與生產 implementer 解耦），故改生產 implementer 再也影響不了它。
    ⇒ 若照 SPEC 原文變異（把 implementer 寫成非法值），本測會**恆綠**，變成廢格。

    改打真正承重的那一環：把沙箱 `eligible` 抽成「沒有任何 CLI 可派家族」。
    此時 `_role_pin.pin_implementer` 必須 **fail-closed 拋錯**（而非早退）⇒ V12 轉紅。
    這一格證明的正是「fail-open 已改 fail-closed」。
    """
    iso = _make_iso(tmp_path)
    base = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
    assert base["rc"] == 0, f"2-① 基線須綠：\n{base['out'][-2000:]}"
    assert base["skipped"] == 0, f"2-① 基線不得有 skip，得 {base['skipped']}"

    roles = iso / "scripts" / "governance_roles.json"
    rd = json.loads(roles.read_text(encoding="utf-8"))
    rd["eligible"] = ["claude"]  # 只剩無 CLI 配方的編排端
    roles.write_text(json.dumps(rd, ensure_ascii=False, indent=2), encoding="utf-8")

    mut = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
    assert mut["rc"] != 0, (
        f"2-① 名冊給不出 CLI 家族時必須轉紅（不得靜默早退）：\n{mut['out'][-2000:]}"
    )
    assert mut["skipped"] == 0, f"2-① 變異後不得以 skip 收場，得 {mut['skipped']}"


# ── 票文條件 2-②：三個 CLI 家族逐一釘定皆可走 impl 路徑 ─────────────


def test_impl_path_works_for_every_cli_family(tmp_path: Path) -> None:
    """2-②：逐一釘定三家 ⇒ 各自 `rc == 0` 且 `skipped == 0`；判準寫**字面** 3。

    🔴 不得寫 `passed == len(review_families)`——那是自我參照，名冊縮成一家時恆真。
    """
    iso = _make_iso(tmp_path)
    fams = _role_pin.cli_dispatchable_families(iso / "scripts")
    assert sorted(fams) == sorted(_EXPECTED_CLI_FAMILIES), (
        f"CLI 可派家族漂移：want={sorted(_EXPECTED_CLI_FAMILIES)} got={sorted(fams)}"
    )
    # 🔴 逐家收 receipt，不用計數器〔`CODEX-R2-P1-05`〕：
    #    `ok += 1` 只證明迴圈跑了三次，不證明「三個各自獨立的 subprocess pass receipt」。
    receipts: dict[str, dict] = {}
    for fam in fams:
        _role_pin.pin_implementer(iso / "scripts", fam)
        r = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
        assert r["rc"] == 0, f"釘 {fam} 後 impl 路徑應綠：\n{r['out'][-2000:]}"
        assert r["skipped"] == 0, f"釘 {fam} 後不得有 skip，得 {r['skipped']}"
        assert r["passed"] == 4, f"釘 {fam} 後應 4 格 per-kind receipt，得 {r['passed']}"
        receipts[fam] = r
    assert len(receipts) == 3, f"期望恰 3 份 receipt，得 {len(receipts)}"
    assert set(receipts) == set(_EXPECTED_CLI_FAMILIES), (
        f"receipt 家族集合與外部字面集合不符：{sorted(receipts)}"
    )


# ── 票文條件 3：名冊與實際 dispatch 分支機械連動 ────────────────────


def test_dispatch_set_equals_review_families(tmp_path: Path) -> None:
    """3-a：`cx_run.sh` 之 dispatch 分支集合 **等於**（非子集）`review_families`。"""
    iso = _make_iso(tmp_path)
    fams = _role_pin.cli_dispatchable_families(iso / "scripts")
    sot = json.loads(
        (iso / "scripts" / "governance_families.json").read_text(encoding="utf-8")
    )["review_families"]
    assert sorted(fams) == sorted(sot), (
        f"dispatch 分支與 review_families 不相等：{sorted(fams)} vs {sorted(sot)}"
    )


def test_review_families_subset_of_eligible(tmp_path: Path) -> None:
    """3-b：`review_families ⊆ eligible`（否則名冊自相矛盾）。"""
    iso = _make_iso(tmp_path)
    rf = set(
        json.loads(
            (iso / "scripts" / "governance_families.json").read_text(encoding="utf-8")
        )["review_families"]
    )
    el = set(
        json.loads(
            (iso / "scripts" / "governance_roles.json").read_text(encoding="utf-8")
        )["eligible"]
    )
    assert rf <= el, f"review_families 不在 eligible 內：{sorted(rf - el)}"


# ══════════════════════════════════════════════════════════════════════
# Task 3.1 — mutation 矩陣（17 格）：證明每一條判定都承重
# ══════════════════════════════════════════════════════════════════════
# 🔴 SPEC 之 ⑫（同批 rebind）**已刪，不得復原**：主委與實作者同批更新常數，
#    機械上與正常施工不可區分（SPEC §C-11 具名排除），寫成 mutation 只會是廢格。
# 🔴 grant 側的格子以**行程內**變異執行（monkeypatch 模組常數 ＋ 假 diff 餵守衛），
#    不需要子程序——被測的是判定函式本身，不是 pytest 的收集行為。
#    role-pin 側的格子才需隔離子程序（要看 rc／passed／skipped）。

import tests.governance.test_govb1_contract_matrix as _CM  # noqa: E402

_GUARDS = (
    "test_waiver_b45_b3_range_does_not_touch_forbidden",
    "test_waiver_b4_range_does_not_touch_forbidden",
    "test_waiver_b5_range_does_not_touch_forbidden",
)


def _guard_verdict(
    monkeypatch: pytest.MonkeyPatch,
    names: list[str],
    renames: list[tuple[str, str]] | None = None,
) -> bool:
    """餵三道守衛一組假 diff；**任一道拒絕**即回 True。

    只攔 `git diff --name-only`／`--name-status`；其餘（錨點、frozen_hashes）走真指令，
    否則守衛會因為別的理由失敗，判定就不可信了。
    `renames` ＝ `[(舊名, 新名), …]`，用來建模 `--name-only` 看不到的 rename／copy。
    """
    real_run = _CM._run
    payload = "\n".join(names) + ("\n" if names else "")
    ns_payload = "".join(f"R100\t{o}\t{n}\n" for o, n in (renames or []))

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(c, 0, payload, "")
        if c[:3] == ["git", "diff", "--name-status"]:
            return subprocess.CompletedProcess(c, 0, ns_payload, "")
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(_CM, "_run", _fake)
    for fn in _GUARDS:
        guard = getattr(_CM, fn, None)
        assert guard is not None, f"守衛 {fn} 不見了 ⇒ 保護真空"
        try:
            guard()
        except AssertionError as exc:
            if "harness" in str(exc) or "禁改前綴" in str(exc):
                return True
            return True  # 因其他斷言拒絕也算拒絕（保守方向）
        except BaseException as exc:  # noqa: BLE001
            if type(exc).__name__ == "Skipped":
                continue
            raise
    return False


def _granted_paths() -> list[str]:
    return sorted(_CM._B49_GRANT_IDENTITY)


# ── ⑦ grant 為空 dict ⇒ 授權檔亦須被拒（不得退化為「全授權」）────────


def test_mut07_empty_grant_rejects_authorized_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = _granted_paths()[0]
    assert not _guard_verdict(monkeypatch, [p]), "前提壞了：授權路徑在基線應被放行"
    monkeypatch.setattr(_CM, "_B49_GRANT_IDENTITY", {})
    assert _guard_verdict(monkeypatch, [p]), "⑦ grant 空集合時必須拒絕，不得視為全授權"


# ── ⑧ diff 含第四個（未授權）harness ⇒ 拒 ───────────────────────────


def test_mut08_unauthorized_harness_still_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rest = sorted(set(_CM._B45_HARNESS) - set(_CM._B49_GRANT_IDENTITY))
    assert rest, "前提壞了：五檔全授權則本格失去意義"
    assert _guard_verdict(monkeypatch, [rest[0]]), f"⑧ 未授權 harness {rest[0]} 必須拒"


# ── ⑨/⑩/⑩b/⑩c 位元組層：授權快照與工作樹不符 ⇒ 拒 ──────────────────


@pytest.mark.parametrize(
    "cell,vector",
    [
        ("mut09_one_byte", b"\n# B-49 MUT09\n"),
        ("mut10_worktree_corrupt", b"\x00CORRUPT"),
        ("mut10c_crlf", b"\r\n"),
    ],
)
def test_mut09_10_10c_worktree_byte_mismatch_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, cell: str, vector: bytes
) -> None:
    """授權檔工作樹內容一被改動（哪怕一個位元組）即失去豁免。

    ⑩c（autocrlf／filter）與 ⑨／⑩ 同一承重點：**逐位元組比對**，
    故以不同 vector 各佔一格，證明不是只擋單一寫法。
    """
    p = _granted_paths()[0]
    _orig = Path.read_bytes

    def _rb(self: Path, _v: bytes = vector) -> bytes:
        # 只對受測路徑動手；其餘檔案照舊，避免變異範圍外溢造成誤判
        return _orig(self) + _v if str(self).endswith(p) else _orig(self)

    monkeypatch.setattr(Path, "read_bytes", _rb)
    assert _guard_verdict(monkeypatch, [p]), f"{cell}：工作樹位元組不符必須拒"


def test_mut10b_skip_worktree_cannot_defeat_bytes_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⑩b：`skip-worktree`／`assume-unchanged` 打不敗位元組比對。

    那兩個旗標只影響 **index**；本機制讀的是 `git cat-file blob` 與工作樹，
    **不經 index** ⇒ 設了旗標也不改變判定。以「index 說沒改、工作樹其實改了」建模。
    """
    p = _granted_paths()[0]
    real_run = _CM._run

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:2] == ["git", "diff"] and "--quiet" in c:
            return subprocess.CompletedProcess(c, 0, "", "")  # index 謊稱乾淨
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(_CM, "_run", _fake)
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"TAMPERED")
    assert not _CM._b49_granted(p), "⑩b：index 旗標不得使位元組比對失效"


# ── ⑪ mode 變更（100644 → 100755）⇒ 身分三元組不符 ⇒ 拒 ─────────────


def test_mut11_mode_change_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """常數側：授權 mode 與 `ls-tree` 三元組不符 ⇒ 拒。"""
    p = _granted_paths()[0]
    want = _CM._B49_GRANT_IDENTITY[p]
    mutated = dict(_CM._B49_GRANT_IDENTITY)
    mutated[p] = want.replace("100644", "100755", 1)
    monkeypatch.setattr(_CM, "_B49_GRANT_IDENTITY", mutated)
    assert not _CM._b49_granted(p), "⑪ mode 不符必須拒（身分是三元組，不只 oid）"


@pytest.mark.parametrize("shape", ["exec_bit", "symlink", "gitlink", "missing"])
def test_mut11b_worktree_shape_probes(tmp_path: Path, shape: str) -> None:
    """⑪b 工作樹側：**真實** chmod／symlink／gitlink 探針，打的是生產判定
    `_b49_worktree_shape_ok`〔`CODEX-R2-P1-02`〕。

    原本只改 grant 常數字串，**沒有看工作樹真實 mode** ⇒ 對一個授權檔 `chmod +x`：
    `ls-tree HEAD` 三元組不變、位元組不變 ⇒ 豁免照舊成立，而 SPEC 明定該情形須拒。
    """
    ok_file = tmp_path / "ok.txt"
    ok_file.write_bytes(b"x")
    assert _CM._b49_worktree_shape_ok(ok_file, "100644"), "基線：普通檔應通過"

    if shape == "exec_bit":
        ok_file.chmod(0o755)
        assert not _CM._b49_worktree_shape_ok(ok_file, "100644"), "chmod +x 後須拒"
        assert _CM._b49_worktree_shape_ok(ok_file, "100755"), "授權 mode 相符則應通過"
    elif shape == "symlink":
        link = tmp_path / "link.txt"
        link.symlink_to(ok_file)
        assert not _CM._b49_worktree_shape_ok(link, "100644"), "symlink 須拒"
    elif shape == "gitlink":
        sub = tmp_path / "sub"
        (sub / ".git").mkdir(parents=True)
        assert not _CM._b49_worktree_shape_ok(sub, "100644"), "gitlink/submodule 須拒"
        assert not _CM._b49_worktree_shape_ok(ok_file, "160000"), "gitlink mode 須拒"
    else:  # missing
        assert not _CM._b49_worktree_shape_ok(tmp_path / "nope", "100644"), "缺檔須拒"


def test_mut11c_shape_check_is_wired_into_granted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⑪c **整合驗證**：形狀檢查必須真的掛在 `_b49_granted` 的路徑上。

    🔴 ⑪b 只打純函式 `_b49_worktree_shape_ok`——反向驗證實測：把
    `_b49_worktree_bytes_match` 裡那行呼叫改成 `if False:`，⑪b 仍 4 passed
    ⇒ 它證明不了整合還在（與 `CODEX-R2-P1-04` 抓到的 ⑬b／⑭ 同型）。
    本格改為讓授權檔的工作樹**看起來帶 exec bit**，要求 `_b49_granted` 轉為 False。
    """
    p = _granted_paths()[0]
    fp = REPO / p
    assert _CM._b49_granted(p), "前提壞了：授權路徑在基線應被授權"

    _orig_lstat = Path.lstat

    def _fake_lstat(self: Path):
        st = _orig_lstat(self)
        if self == fp:
            return os.stat_result(
                (st.st_mode | 0o111,) + tuple(st)[1:]
            )
        return st

    monkeypatch.setattr(Path, "lstat", _fake_lstat)
    assert not _CM._b49_granted(p), (
        "⑪c 工作樹 exec bit 與授權 mode 不符卻仍授權 ⇒ 形狀檢查沒掛在 _b49_granted 上"
    )


# ── ⑬ 授權檔刪除／改名 ⇒ 拒 ──────────────────────────────────────────


def test_mut13a_deleted_authorized_path_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """刪除：`ls-tree` 取不到 ⇒ 身分 None ⇒ 拒（fail-closed，不得回退讀工作樹）。"""
    p = _granted_paths()[0]
    real_run = _CM._run

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:3] == ["git", "ls-tree", "HEAD"]:
            return subprocess.CompletedProcess(c, 0, "", "")
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(_CM, "_run", _fake)
    assert not _CM._b49_granted(p), "⑬a 身分取不到必須判不符"


def test_mut13b_rename_old_name_is_recovered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """改名：`--name-only` 只給新名 ⇒ 舊名須由 `--name-status -M -C` 補回並被拒。

    〔`CODEX-CONSULT-R1-P0-02`〕不補回舊名 ⇒ 改個名就把 harness 洗出保護範圍。
    """
    victim = sorted(set(_CM._B45_HARNESS) - set(_CM._B49_GRANT_IDENTITY))[0]
    new_name = "tests/governance/_renamed_probe.py"
    real_run = _CM._run

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(c, 0, new_name + "\n", "")
        if c[:3] == ["git", "diff", "--name-status"]:
            return subprocess.CompletedProcess(
                c, 0, f"R100\t{victim}\t{new_name}\n", ""
            )
        return real_run(cmd, *a, **kw)

    # 🔴 必須經**三道守衛**判定，不得只呼叫 helper〔`CODEX-R2-P1-04`〕：
    #    codex 在隔離 clone 移除 `names |= _rename_old_names(...)` 三處整合後，
    #    原寫法（直呼 helper）仍 1 passed ⇒ 那一格不承重，是假格。
    assert not _guard_verdict(monkeypatch, [new_name]), (
        "前提壞了：新名本身不在保護清單，不帶 rename 資訊時應放行"
    )
    assert _guard_verdict(monkeypatch, [new_name], renames=[(victim, new_name)]), (
        "⑬b 改名後舊名未被守衛看見 ⇒ 改名即可把 harness 洗出保護範圍"
    )
    monkeypatch.setattr(_CM, "_run", _fake)
    assert victim in _CM._rename_old_names("dummy..range"), "⑬b helper 本身也須補回舊名"


def test_mut13c_rename_probe_fails_closed_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rename 偵測失敗**不得**靜默回空集合（那等於改名就放行）。"""
    real_run = _CM._run

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:3] == ["git", "diff", "--name-status"]:
            return subprocess.CompletedProcess(c, 128, "", "fatal: boom")
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(_CM, "_run", _fake)
    with pytest.raises(AssertionError):
        _CM._rename_old_names("dummy..range")


# ── ⑯ 閉合證據之具名 selector 被改名／刪除 ⇒ 關票證據失效 ─────────────


def test_mut16_closure_selector_rename_breaks_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mutated = ("test_selector_that_does_not_exist",) + _CM._B49_CLOSURE_SELECTORS[1:]
    monkeypatch.setattr(_CM, "_B49_CLOSURE_SELECTORS", mutated)
    with pytest.raises(AssertionError, match="具名 selector"):
        _CM._assert_b49_closure_evidence()


# ── ⑮ 票 CLOSED 但證據缺 ⇒ 炸彈必紅 ────────────────────────────────


def test_mut17_hollow_selector_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    """⑰ selector 被掏空（body 只剩 docstring）⇒ 閉合證據須拒。

    主委反向驗證實測：只驗 `rc`／`passed` 時，掏空的 selector 照樣 `1 passed`
    ⇒ 炸彈仍綠。本格打的是 `_b49_selector_is_substantive` **與其整合**。
    """
    real_src = (REPO / _CM._B49_CLOSURE_FILE).read_text(encoding="utf-8")
    target = _CM._B49_CLOSURE_SELECTORS[0]
    assert _CM._b49_selector_is_substantive(real_src, target), "基線：真實 selector 應有斷言"

    gutted = 'def %s():\n    """gutted"""\n    pass\n' % target
    assert not _CM._b49_selector_is_substantive(gutted, target), "掏空的 selector 須判為無實質"
    assert not _CM._b49_selector_is_substantive(real_src, "no_such_selector_name"), (
        "不存在的 selector 須判為無實質（fail-closed）"
    )

    # 整合：判定回 False 時，閉合證據必須拒（不得只在純函式層成立）
    monkeypatch.setattr(_CM, "_b49_selector_is_substantive", lambda *_a, **_k: False)
    with pytest.raises(AssertionError, match="掏空"):
        _CM._assert_b49_closure_evidence()


def test_mut15_closed_without_evidence_turns_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """票標 CLOSED 而閉合證據檔不存在 ⇒ `_assert_b49_closure_evidence` 拋錯。"""
    monkeypatch.setattr(_CM, "_B49_CLOSURE_FILE", "tests/governance/_no_such_file.py")
    with pytest.raises(AssertionError, match="不存在"):
        _CM._assert_b49_closure_evidence()


# ── ⑥ `_role_pin` 不得硬編家族三元組 ─────────────────────────────────


def test_mut06_role_pin_has_no_hardcoded_family_triple() -> None:
    """票 B-49 閉合條件 3：合法家族一律由 SoT 導出，禁字面三元組。

    🔴 **不得用字串 `in` 掃全檔**——`_role_pin` 的 docstring 逐字寫著
    「不得出現 `("codex", "grok", "composer")` 這種字面三元組」，那是**規則敘述**，
    掃全檔會把說明本身當成違規（用散文測散文）。改走 AST：只看**程式碼**中的字面值，
    docstring 由 `ast.get_docstring` 排除。
    """
    import ast

    tree = ast.parse(
        (REPO / "tests" / "governance" / "_role_pin.py").read_text(encoding="utf-8")
    )
    docstrings = {ast.get_docstring(tree)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstrings.add(ast.get_docstring(node))
    hits = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value in _EXPECTED_CLI_FAMILIES
        and n.value not in docstrings
    ]
    assert not hits, f"_role_pin 程式碼出現硬編家族名 {hits} ⇒ 與 SoT 脫鉤"


# ── ⑤ roles/cx_run 漂移 ⇒ fail-closed ───────────────────────────────


def test_mut05_family_sot_drift_fails_closed(tmp_path: Path) -> None:
    """`governance_families.json` 與 `cx_run.sh` 的可派家族不一致 ⇒ 當場拋錯。"""
    iso = _make_iso(tmp_path)
    sot = iso / "scripts" / "governance_families.json"
    d = json.loads(sot.read_text(encoding="utf-8"))
    d["review_families"] = [f for f in d["review_families"]][:1]
    sot.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(AssertionError, match="漂移"):
        _role_pin.cli_dispatchable_families(iso / "scripts")


# ── ④ cx_run dispatch 分支縮成真子集 ⇒ 3-a 轉紅 ─────────────────────


def test_mut04_dispatch_proper_subset_turns_red(tmp_path: Path) -> None:
    iso = _make_iso(tmp_path)
    cx = iso / "scripts" / "cx_run.sh"
    src = cx.read_text(encoding="utf-8")
    victim = _EXPECTED_CLI_FAMILIES[-1]
    assert f"\n    {victim})" in src or f"\n  {victim})" in src, "找不到可拿掉的分支錨點"
    cx.write_text(src.replace(f"{victim})", f"_removed_{victim})"), encoding="utf-8")
    with pytest.raises(AssertionError, match="漂移"):
        _role_pin.cli_dispatchable_families(iso / "scripts")


# ── ③ 合法家族縮成一個 ⇒ 2-② 之「恰 3 家」轉紅 ─────────────────────


def test_mut03_single_family_breaks_three_family_receipt(tmp_path: Path) -> None:
    """把可派家族縮成一家 ⇒ `pin_implementer` 之兩家 review 下限 fail-closed。"""
    iso = _make_iso(tmp_path)
    fams = _role_pin.cli_dispatchable_families(iso / "scripts")
    roles = iso / "scripts" / "governance_roles.json"
    rd = json.loads(roles.read_text(encoding="utf-8"))
    rd["eligible"] = [fams[0]]
    roles.write_text(json.dumps(rd, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(AssertionError, match="review pool"):
        _role_pin.pin_implementer(iso / "scripts", fams[0])


# ── ① `pytest.skip` 死碼：1-a 須紅、1-b **不**紅 ────────────────────


def test_mut01_dead_skip_reddens_1a_but_not_1b(tmp_path: Path) -> None:
    """🔴 這一格正是要證明 1-a／1-b **拆開的必要性**。

    把 `pytest.skip` 加回去、但釘定仍在（⇒ 條件永不成立，是**死碼**）：
      · 1-a（原始碼層）**必須紅**——逃生口存在本身就是病
      · 1-b（行為層）**不會紅**——死碼不影響 4 格全過
    若只有 1-b，這個回歸就溜過去了。
    """
    iso = _make_iso(tmp_path)
    tgt = iso / "tests" / "governance" / "test_stamp_taskid_inject.py"
    src = tgt.read_text(encoding="utf-8")
    # 🔴 先取 V12 的片段再注入：`brief_rel = ...` 在本檔出現多次，
    #    直接對全檔 replace(count=1) 會打到**別的函式**（主委實測踩到）。
    seg = _fn_source(tgt, V12_FN)
    anchor = '    brief_rel = "handoffs/brief.md"'
    assert anchor in seg, "V12 片段內找不到注入錨點"
    new_seg = seg.replace(
        anchor,
        '    if fam == "no-such-family-ever":\n'
        '        pytest.skip("dead code")\n' + anchor,
        1,
    )
    assert src.count(seg) == 1, "V12 片段在檔內不唯一 ⇒ 注入位置有歧義"
    tgt.write_text(src.replace(seg, new_seg, 1), encoding="utf-8")

    # 1-b：行為層不受影響（死碼）
    r = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
    assert r["rc"] == 0 and r["passed"] == 4 and r["skipped"] == 0, (
        f"① 死碼不應改變行為層：{r['out'][-1500:]}"
    )
    # 1-a：原始碼層必須抓到
    seg = _fn_source(tgt, V12_FN)
    assert "skip" in seg.lower(), "① 1-a 沒抓到死碼逃生口 ⇒ 兩格拆開就失去意義"


# ── ② 拿掉一個 parametrize 值 ⇒ 1-b 的 `passed == 4` 轉紅 ───────────


def test_mut02_missing_kind_breaks_four_receipt(tmp_path: Path) -> None:
    iso = _make_iso(tmp_path)
    tgt = iso / "tests" / "governance" / "test_stamp_taskid_inject.py"
    src = tgt.read_text(encoding="utf-8")
    old = '@pytest.mark.parametrize("kind", ("review", "consult", "closure", "impl"))'
    assert old in src, "找不到 parametrize 錨點"
    tgt.write_text(
        src.replace(
            old, '@pytest.mark.parametrize("kind", ("review", "consult", "impl"))', 1
        ),
        encoding="utf-8",
    )
    r = _run_iso(iso, f"{STAMP_FILE}::{V12_FN}")
    assert r["passed"] != 4, "② 少一個 kind 時 `passed == 4` 必須轉紅"


# ── ⑭ 隔離副本之 scripts 是 symlink ⇒ runner 直接紅 ─────────────────


def test_mut14_symlink_scripts_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """runner 判準①：實體 copy。symlink 穿透會讓子程序改到主 repo。

    🔴 必須經 `_make_iso`（runner 真正走的入口），不得只直呼 `_assert_physical_copy`
    〔`CODEX-R2-P1-04`〕：codex 在隔離 clone 移除 `_make_iso` 內那一行呼叫後，
    原寫法仍 1 passed ⇒ 假格。改為把 `copytree` 換成建 symlink，
    再要求 `_make_iso` **自己**擋下來——整合一旦被拿掉，本格立刻轉綠失敗。
    """

    def _fake_copytree(src, dst, **kw):
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        if not Path(dst).exists():
            Path(dst).symlink_to(Path(src))
        return dst

    monkeypatch.setattr(shutil, "copytree", _fake_copytree)
    with pytest.raises(AssertionError, match="symlink"):
        _make_iso(tmp_path)


# ══════════════════════════════════════════════════════════════════════
# Task 3.2 — 行為不變對照（OLD vs NEW）
# ══════════════════════════════════════════════════════════════════════
# 證明「grant 常數不存在」時，三道守衛對**既有**輸入的判定逐字無改變。
# 🔴 baseline 用 **immutable pre-B49 SHA**，不得寫 `HEAD`（`CODEX-R1-P1-04`）：
#    HEAD 會隨施工 commit 前移，第二個 commit 之後 baseline 就變成「已含 grant 的版本」
#    ⇒ 對照退化成自己比自己，恆真。
_PRE_B49_SHA = "835c3d35"


def _load_pre_b49_module():
    """把 pre-B49 版的契約矩陣載成獨立模組（`__file__` 指回真實路徑，`REPO` 才解得對）。"""
    import types

    p = subprocess.run(
        ["git", "show", f"{_PRE_B49_SHA}:tests/governance/test_govb1_contract_matrix.py"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0 and p.stdout, f"取不到 pre-B49 baseline：{p.stderr}"
    assert "_B49_GRANT_IDENTITY" not in p.stdout, (
        f"{_PRE_B49_SHA} 已含 grant 常數 ⇒ 這不是施工前的版本，對照無效"
    )
    real_path = str(REPO / "tests" / "governance" / "test_govb1_contract_matrix.py")
    mod = types.ModuleType("_cm_pre_b49")
    mod.__file__ = real_path
    exec(compile(p.stdout, real_path, "exec"), mod.__dict__)  # noqa: S102
    return mod


def _verdict_of(mod, monkeypatch: pytest.MonkeyPatch, names: list[str]) -> bool:
    """對指定模組餵同一組假 diff，回傳「是否有守衛拒絕」。"""
    real_run = mod._run
    payload = "\n".join(names) + ("\n" if names else "")

    def _fake(cmd, *a, **kw):
        c = list(cmd)
        if c[:3] == ["git", "diff", "--name-only"]:
            return subprocess.CompletedProcess(c, 0, payload, "")
        if c[:3] == ["git", "diff", "--name-status"]:
            return subprocess.CompletedProcess(c, 0, "", "")
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(mod, "_run", _fake)
    for fn in _GUARDS:
        guard = getattr(mod, fn, None)
        assert guard is not None, f"{mod.__name__} 缺守衛 {fn}"
        try:
            guard()
        except AssertionError:
            return True
        except BaseException as exc:  # noqa: BLE001
            if type(exc).__name__ == "Skipped":
                continue
            raise
    return False


_PARITY_CASES = [
    ("empty", []),
    ("ordinary_file", ["scripts/gate.sh"]),
    ("unauthorized_harness", ["tests/governance/test_cxrun_stamp_prompt.py"]),
    ("second_unauthorized_harness", ["tests/governance/test_completeness_idlike_fp.py"]),
    ("govb1_prefix_not_granted", ["docs/GOVB1_INPUT_QUALITY_SPEC.md"]),
    ("frozen_hashes", ["scripts/govb1_frozen_hashes.txt"]),
    ("mixed", ["scripts/gate.sh", "tests/governance/test_cxrun_stamp_prompt.py"]),
]


@pytest.mark.parametrize("label,names", _PARITY_CASES, ids=[c[0] for c in _PARITY_CASES])
def test_task32_old_new_behaviour_parity(
    monkeypatch: pytest.MonkeyPatch, label: str, names: list[str]
) -> None:
    """OLD 與 NEW 對**未授權**輸入的判定必須逐格相同。

    只比未授權輸入——授權路徑的判定**本來就該不同**（那正是本票的交付內容），
    把它混進來比會是自欺。
    """
    granted = set(_CM._B49_GRANT_IDENTITY)
    assert not (set(names) & granted), f"{label} 混入授權路徑 ⇒ 對照失去意義"
    old = _verdict_of(_load_pre_b49_module(), monkeypatch, names)
    new = _verdict_of(_CM, monkeypatch, names)
    assert old == new, f"{label}：行為改變 old_reject={old} new_reject={new}"


def test_task32_granted_paths_are_the_only_behaviour_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """反向：授權路徑上 OLD 拒、NEW 放 —— 差異**恰好**落在授權集合，不多不少。"""
    pre = _load_pre_b49_module()
    for p in sorted(_CM._B49_GRANT_IDENTITY):
        old = _verdict_of(pre, monkeypatch, [p])
        new = _verdict_of(_CM, monkeypatch, [p])
        assert old is True, f"{p}：pre-B49 應拒（否則本票沒有解決任何問題）"
        assert new is False, f"{p}：授權後應放行"
