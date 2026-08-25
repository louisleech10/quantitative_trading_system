#!/usr/bin/env python3
"""mutation runner 之隔離執行環境（git worktree）。

🔴 為何存在（2026-08-25 使用者授權根治）：
專案既有之 mutation 做法（`scripts/verify_mutation.sh`，2026-07-25）與 `handoffs/` 之各
epic runner 都是「備份 → 改**真實** repo 檔 → 跑測試 → 還原」。單一執行者時完全正確
（trap／context manager 保證還原），但**不是併發安全**：多個執行者同時跑會互相破壞彼此的
baseline，症狀＝「部分條目 pre_rc != 0 而未執行 ⇒ 整份 NOT-CLOSED」。
已實際出現兩次（GAP-3 B1 R5、survivor R2），兩次都由無併發重跑證實為假失敗。

兩種用法：
  1. 官方 CLI —— `bash scripts/verify_mutation.sh <檔> <原> <變異> <pytest目標>`
     （即 `python scripts/mutation_worktree.py verify ...`，見 `_run_verify`）
  2. 程式介面 —— `with IsolatedWorktree() as wt:`，供 `handoffs/` 之多條 mutation runner 使用
自檢：`python scripts/mutation_worktree.py`（不帶參數）印出隔離副本看得到什麼。

本模組讓每個執行者在**自己的 git worktree 副本**內改檔，因此三家委員可**平行**重跑
（不是排隊等鎖）。副作用另有好處：`__pycache__` 與 pytest cache 也各自隔離
（codex 於 B1 R5 報過該不穩定）。

隔離內容：
  - worktree 由 `HEAD` 建立（detached），故含全部**已提交**之產品碼與測試
  - **未提交之 tracked 改動**以 `git diff HEAD` 套入（否則驗的是舊碼）
  - **未追蹤但非 ignored** 之檔（例如剛寫好還沒 commit 的測試）逐一複製
  - gitignore 之外部依賴（`data_cache`）以符號連結掛入；`venv` 不連結，
    改以主 repo 之絕對路徑 python 執行（venv 內含絕對路徑，連結反而易錯）

誠實邊界：
  - 只隔離**檔案**。若測試會寫共用的外部資源（真實 DB、固定 port、`data_cache` 內容），
    仍會互相干擾——本模組不處理那類。目前各 runner 之標的皆為純檔案／記憶體測試。
  - `data_cache` 是**共用符號連結**（唯讀使用）；若某測試會**寫**它，隔離無效。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: 🔴 **不得**掛入之 ignored 項（掛了就失去隔離或必壞）：
#:   - `__pycache__`／`.pytest_cache`：正是要隔離的東西（codex 於 B1 R5 報過其不穩定）
#:   - `venv`：內含絕對路徑；本模組改用主 repo 之 python 絕對路徑執行
#:   - `.git`／worktree 自己的暫存
#:   - `.claude/tmp`／`.claude/worktrees`：session 暫存，2026-08-25 實測 `.claude/tmp` 為 **21 GB**
_SKIP_IGNORED = (
    "__pycache__", ".pytest_cache", "venv/", ".git/", ".mypy_cache", ".ruff_cache",
    ".claude/tmp/", ".claude/worktrees/",
)

#: 🔴 以**複製**（而非符號連結）掛入之 ignored 前綴 —— 判準＝「測試會**寫**它」。
#: 符號連結會讓 worktree 內的寫入**穿透回主 repo**，等同沒隔離。
#: `.claude/gate/` 存 gate token／audit log／ts_stamp，治理測試會寫；而 `verify_mutation.sh`
#: 的主要用途正是變異治理腳本（其 docstring 範例即 `verify_task_provenance.py`）⇒ 必須複製。
#: 誠實邊界：此清單靠人維護。其餘 ignored 路徑（`data_cache/`、`handoffs/`、`*.h5` fixture）
#: 皆以**唯讀**假設符號連結掛入；若日後有測試會寫它們，隔離對那條無效——請把前綴加進本表。
_COPY_IGNORED_PREFIXES = (".claude/",)


def _ignored_paths() -> list[str]:
    """repo 內全部 gitignore 之項目（相對路徑）。

    🔴 為何不手列白名單（2026-08-25 踩過）：先前只手列 `data_cache`，
    結果 `tests/golden/la0/inputs/*.h5` 因 `.gitignore` 之 `*.h5` 而不在 worktree ⇒
    e2e 測試「fixture 缺席」全紅。主委當時只驗了**目錄** `git check-ignore tests/golden`
    得空輸出就下結論「fixture 在版控內」——那是「比對範圍過寬」，驗錯了對象。
    ⇒ 改為**逐項問 git**，不靠人列。granularity 亦由 git 決定：
      目錄整個 ignored ⇒ 回目錄；目錄內僅部分 ignored ⇒ 回個別檔。
    """
    out = _git("status", "--porcelain", "--ignored=matching", "-z").stdout
    paths = []
    for entry in out.split("\0"):
        if not entry.startswith("!! "):
            continue
        rel = entry[3:]
        if any(s in rel for s in _SKIP_IGNORED):
            continue
        paths.append(rel)
    return paths


def _git(*args, cwd=None, check=True, capture=True):
    return subprocess.run(
        ["git", *args], cwd=str(cwd or REPO), check=check,
        capture_output=capture, text=True,
    )


def venv_python() -> str:
    """主 repo 之 venv python 絕對路徑（worktree 不複製 venv）。"""
    p = REPO / "venv" / "bin" / "python"
    return str(p) if p.exists() else sys.executable


class IsolatedWorktree:
    """`with IsolatedWorktree() as wt:` — wt 為隔離副本之根目錄 Path。"""

    def __init__(self, prefix: str = "mutwt_"):
        self._prefix = prefix
        self.path: Path | None = None
        self._tmp: Path | None = None

    def __enter__(self) -> Path:
        self._tmp = Path(tempfile.mkdtemp(prefix=self._prefix))
        self.path = self._tmp / "wt"

        # git worktree add 會寫主 repo 之 .git/worktrees/；併發時偶爾撞 index.lock ⇒ 退避重試
        last = None
        for attempt in range(5):
            try:
                _git("worktree", "add", "--detach", "--quiet", str(self.path), "HEAD")
                last = None
                break
            except subprocess.CalledProcessError as exc:  # noqa: PERF203
                last = exc
                time.sleep(0.4 * (attempt + 1))
        if last is not None:
            raise RuntimeError(f"git worktree add 失敗: {last.stderr}") from last

        # 未提交之 tracked 改動：不套的話驗到的是舊碼（假綠來源）
        diff = _git("diff", "HEAD").stdout
        if diff.strip():
            proc = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", "-"],
                cwd=str(self.path), input=diff, text=True, capture_output=True,
            )
            if proc.returncode != 0:
                self.__exit__(None, None, None)
                raise RuntimeError(f"套用未提交改動失敗: {proc.stderr}")

        # 未追蹤但非 ignored 之檔（剛寫好還沒 commit 的測試等）
        untracked = _git("ls-files", "--others", "--exclude-standard").stdout.split("\n")
        for rel in filter(None, (r.strip() for r in untracked)):
            src = REPO / rel
            if not src.is_file():
                continue
            dst = self.path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        # gitignore 之外部依賴：逐項掛入。會被寫的用**複製**，其餘用符號連結（唯讀假設）。
        linked = copied = 0
        for rel in _ignored_paths():
            src = REPO / rel
            if not src.exists():
                continue
            dst = self.path / rel.rstrip("/")
            if dst.exists() or dst.is_symlink():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file() and rel.startswith(_COPY_IGNORED_PREFIXES):
                shutil.copy2(src, dst)
                copied += 1
            else:
                os.symlink(src, dst)
                linked += 1
        self.linked_ignored = linked
        self.copied_ignored = copied

        return self.path

    def __exit__(self, *exc) -> bool:
        if self.path is not None:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.path)],
                cwd=str(REPO), capture_output=True, text=True,
            )
        if self._tmp is not None:
            shutil.rmtree(self._tmp, ignore_errors=True)
        # 保險：worktree 清單可能留下失效項
        subprocess.run(["git", "worktree", "prune"], cwd=str(REPO), capture_output=True)
        return False


def _run_verify(file_rel: str, old: str, new: str, target: str) -> int:
    """`scripts/verify_mutation.sh` 之實作：改壞→須紅→還原→須綠，全程在隔離副本內。

    stdout 之判詞字串**與 2026-07-25 舊版逐字相同**（委員報告會引用它們），勿改。
    """
    # 🔴 隔離破口 fail-closed：`Path(wt) / "/abs/x"` 在 pathlib 等於 `/abs/x`，
    #   絕對路徑會**靜默打回主 repo**；`..` 同理。一律拒收，不嘗試修正。
    if Path(file_rel).is_absolute() or ".." in Path(file_rel).parts:
        sys.stderr.write(f"ERROR: <檔> 須為 repo 相對路徑且不含 '..'（收到: {file_rel}）\n")
        return 2

    py = venv_python()
    with IsolatedWorktree(prefix="vmut_") as wt:
        print(f"[verify_mutation] 隔離副本 = {wt}（主 repo 不被改動）")
        path = wt / file_rel
        if not path.is_file():
            sys.stderr.write(f"ERROR: 檔不存在於隔離副本: {file_rel}\n")
            return 2
        original = path.read_text(encoding="utf-8")
        if old not in original:
            sys.stderr.write("ERROR: 檔內找不到要變異的字串(結構已改?):\n  %r\n" % old)
            return 2
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        print("[verify_mutation] 已套用變異(替換 1 處)")

        def pytest_ok() -> bool:
            proc = subprocess.run([py, "-m", "pytest", target, "-q", "--tb=line"],
                                  cwd=str(wt), capture_output=True, text=True)
            return proc.returncode == 0

        print(f"[verify_mutation] === 變異後跑 {target}(期望:轉紅) ===")
        if pytest_ok():
            sys.stderr.write("[verify_mutation] ❌ 變異後測試仍**綠** → 這測試抓不到該抓的(假綠/弱 oracle)\n")
            return 1
        print("[verify_mutation] ✓ 變異後轉紅(正確)")

        path.write_text(original, encoding="utf-8")
        print(f"[verify_mutation] === 還原後跑 {target}(期望:轉綠) ===")
        if not pytest_ok():
            sys.stderr.write("[verify_mutation] ❌ 還原後仍紅 → 測試本身有問題(或還原不完整)\n")
            return 1
        print("[verify_mutation] ✅ 通過:變異→紅、還原→綠(此守衛是真 oracle)")
        return 0


def _selftest() -> int:
    iso = IsolatedWorktree()
    with iso as wt:
        print(f"worktree = {wt}")
        print(f"  符號連結之 ignored 項數    = {iso.linked_ignored}")
        print(f"  複製之 ignored 項數        = {iso.copied_ignored}")
        print(f"  survivor_contract.py 存在  = {(wt / 'momentum/Analysis/survivor_contract.py').exists()}")
        print(f"  data_cache 連結            = {(wt / 'data_cache').exists()}")
        # 🔴 逐檔驗，不驗目錄——驗目錄正是先前漏掉 *.h5 的原因
        h5 = sorted((wt / "tests/golden/la0/inputs").glob("ETHUSDT_12h_*_a0_tail2000.h5"))
        print(f"  la0 e2e fixture(.h5) 存在  = {bool(h5)}  {h5[0].name if h5 else ''}")
        print(f"  __pycache__ 未被連結       = {not (wt / 'momentum/__pycache__').is_symlink()}")
        # 🔴 .claude/gate 須為**複製**（可寫且不外洩），不得是連結
        tok = wt / ".claude/gate/dispatch.token"
        print(f"  .claude/gate 為複製非連結  = {tok.is_file() and not tok.is_symlink()}")
        print(f"  .claude/tmp 未掛入(21GB)   = {not (wt / '.claude/tmp').exists()}")
        print(f"  venv python                = {venv_python()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "verify":
        if len(sys.argv) != 6:
            sys.stderr.write("用法: python scripts/mutation_worktree.py verify <檔> <原> <變異> <pytest目標>\n")
            raise SystemExit(2)
        raise SystemExit(_run_verify(*sys.argv[2:6]))
    raise SystemExit(_selftest())
