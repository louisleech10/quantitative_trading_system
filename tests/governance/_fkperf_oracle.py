"""FKPERF 差分 harness（docs/FKPERF_SPEC.md Task 0.1）。

oracle＝`git show ORACLE_COMMIT:scripts/gen_fact_key_blocks.sh`（切換前之 bash 實作）。每筆語料建兩個同形沙箱：
同一輸入樹＋註冊表引用之未追蹤 receipt，oracle 沙箱放 oracle 入口、新實作沙箱另放新核心（與新入口）；
兩邊於相同 env／參數／stdin／相對 cwd 下各跑一次，比對 stdout、stderr、rc 與沙箱全樹寫後位元組、權限位。
唯一正規化：兩沙箱根目錄路徑互換（寫死於 `normalize`）。

輸入樹＝`git archive ORACLE_COMMIT -- <SANDBOX_PATHS>`：生成器讀取之路徑（入口、註冊表、rows_source、receipt、
ticket_universe、宿主檔、status／mechanism scope、settings.json）皆在其內；整庫 archive 單份 885MB 不可行。
2026-09-24 主委實跑：此樹下 oracle emit／--check／--write 皆 rc=0（建樹 0.9s、26MB）。
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
# 實作起點 commit：bash 實作最後一次修改所在之 commit（SPEC Task 0.1「寫死於 helper」）
ORACLE_COMMIT = "4bdc2d562543"
ENTRY_REL = "scripts/gen_fact_key_blocks.sh"
CORE_REL = "scripts/_gen_fact_key_blocks.py"
REG_REL = "scripts/fact_keys.json"
SANDBOX_PATHS = ("scripts", "docs", "白話說明", "HANDOFF.md", ".claude/settings.json",
                 "handoffs/20260801-GOV-AMEND-BACKLOG.md")  # 後者為 ticket_universe --check 之輸入（缺則該檢查略過）
_SANDBOX_DROP = ("docs/site",)  # 生成之 HTML，生成器不讀


@dataclass(frozen=True)
class RunOut:
    """單次呼叫之觀測：rc、stdout、stderr，與沙箱全樹寫後之（位元組, 權限位）。"""

    rc: int
    stdout: bytes
    stderr: bytes
    files: Dict[str, Tuple[bytes, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    """一筆差分語料：模式、參數、沙箱建法，與 oracle 應命中之預期分支標籤。

    `env`／`oracle_env`／`new_env` 之值可含 `{root}`，執行時代換為該沙箱根目錄。
    `invoke`＝相對 `cwd` 呼叫入口之路徑（`--help` 之相對路徑與 symlink 語料用）。
    `expect_new`＝C-5 前置例外配對：新實作一側之 (rc, stderr 首行)；只准該具名訊息行不同，其餘全等。"""

    case_id: str
    args: Tuple[str, ...]
    build: Callable[[Path], None]           # 於沙箱根目錄建樹（兩沙箱各呼叫一次）
    expect_rc: int                          # oracle 應得之 rc
    expect_first_line: str                  # rc≠0：stderr 首行；rc=0：stdout 首行
    stdin: Optional[bytes] = None
    env: Dict[str, str] = field(default_factory=dict)
    watch_files: Tuple[str, ...] = ()       # 寫檔語料之宿主檔（相對沙箱根）；寫後快照須含之（全樹皆比對，見 snapshot_tree）
    entry: str = "core"                     # 新實作之呼叫方式：core＝直呼核心、entry＝經入口檔
    invoke: str = ENTRY_REL
    cwd: str = "."
    oracle_env: Dict[str, str] = field(default_factory=dict)
    new_env: Dict[str, str] = field(default_factory=dict)
    expect_new: Optional[Tuple[int, str]] = None
    script_rel: str = ENTRY_REL              # 入口於沙箱根下之位置（錄製語料之生成器位於錄得之樹內；核心置於同目錄）
    unset_env: Tuple[str, ...] = ()          # 呼叫時自環境移除之鍵（錄製語料：原呼叫之 env 缺此鍵）


def core_rel(case: Case) -> str:
    """新核心於沙箱根下之位置：與入口同目錄。"""
    return os.path.join(os.path.dirname(case.script_rel), os.path.basename(CORE_REL))


def _oracle_blob(rel: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ORACLE_COMMIT}:{rel}"],
                          capture_output=True, check=True).stdout


def _copy_receipts(root: Path) -> None:
    reg = (root / REG_REL).read_text(encoding="utf-8")
    for rel in sorted(set(re.findall(r"receipt:([^\s\"，；）)]+)", reg))):
        src, dst = REPO / rel, root / rel
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def build_sandbox_tree(root: Path, *, omit: Sequence[str] = (), git_init: bool = True, minimal: bool = False) -> None:
    """以 `git archive ORACLE_COMMIT -- SANDBOX_PATHS` 建輸入樹＋註冊表引用之 receipt；`omit` 指定要刪之相依檔。
    `minimal=True`：只放入口及註冊表，比照既有 `test_empty_registry_is_rc_zero_not_failure` 之沙箱
    （完整樹下空註冊表會先撞交接投影檢查，2026-09-23 主委實測）。"""
    root.mkdir(parents=True, exist_ok=True)
    if minimal:
        (root / "scripts").mkdir(exist_ok=True)
        (root / ENTRY_REL).write_bytes(_oracle_blob(ENTRY_REL))
        (root / REG_REL).write_bytes(_oracle_blob(REG_REL))
    else:
        ar = subprocess.run(["git", "-C", str(REPO), "archive", ORACLE_COMMIT, "--", *SANDBOX_PATHS],
                            capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(root)], input=ar, check=True)
        for rel in _SANDBOX_DROP:
            shutil.rmtree(root / rel, ignore_errors=True)
        _copy_receipts(root)
    for rel in omit:
        p = root / rel
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        elif p.exists() or p.is_symlink():
            p.unlink()
    if git_init:
        subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)


def build_current_tree(root: Path, include_tests: bool = True) -> None:
    """以目前工作樹之受管檔（SANDBOX_PATHS 範圍，含新入口與核心）＋註冊表引用之 receipt 建樹並 `git init`（切換後驗收用）。"""
    root.mkdir(parents=True, exist_ok=True)
    files = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--", *SANDBOX_PATHS],
                           capture_output=True, check=True).stdout.split(b"\0")
    for raw in files:
        if not raw:
            continue
        rel = raw.decode("utf-8")
        if any(rel == d or rel.startswith(d + "/") for d in _SANDBOX_DROP):
            continue
        src, dst = REPO / rel, root / rel
        if not src.exists() and not src.is_symlink():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            os.symlink(os.readlink(src), dst)
        else:
            shutil.copy2(src, dst)
    for rel in (("tests", "pytest.ini", "conftest.py") if include_tests else ()):  # 巢狀 pytest（Task 4.2）所需；錄製語料之 repo 側不需
        src = REPO / rel
        if src.is_dir():
            files = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--", rel],
                                   capture_output=True, check=True).stdout.split(b"\0")
            for raw in files:
                if raw:
                    r = raw.decode("utf-8")
                    if (REPO / r).is_file():
                        (root / r).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(REPO / r, root / r)
        elif src.is_file():
            shutil.copy2(src, root / rel)
    _copy_receipts(root)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)


def make_pair(tmp_path: Path, case: Case) -> Tuple[Path, Path]:
    """建 oracle 沙箱與新實作沙箱（同一輸入樹、各自完整相依檔）；兩根目錄名等長，正規化只做字面互換。"""
    oroot, nroot = tmp_path / "o", tmp_path / "n"
    for root in (oroot, nroot):
        case.build(root)
    (oroot / case.script_rel).parent.mkdir(parents=True, exist_ok=True)
    (oroot / case.script_rel).write_bytes(_oracle_blob(ENTRY_REL))
    (nroot / core_rel(case)).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / CORE_REL, nroot / core_rel(case))
    if case.entry == "entry":
        shutil.copy2(REPO / ENTRY_REL, nroot / case.script_rel)
    return oroot, nroot


def _env(root: Path, *parts: Dict[str, str], unset: Sequence[str] = ()) -> Dict[str, str]:
    env = dict(os.environ)
    for key in unset:
        env.pop(key, None)
    for part in parts:  # realpath 形：與 `expected_first` 之 `{root}` 代換同形（macOS /var ↔ /private/var）
        env.update({k: v.replace("{root}", str(root.resolve())) for k, v in part.items()})
    return env


# 兩沙箱依設計不同之檔（oracle 入口 vs 新核心／新入口）與版本庫、位元組碼快取，不入寫後快照
_SNAPSHOT_SKIP_DIRS = (".git", "__pycache__")
_SNAPSHOT_SKIP_FILES = (ENTRY_REL, CORE_REL)


def snapshot_tree(root: Path, skip: Sequence[str] = _SNAPSHOT_SKIP_FILES) -> Dict[str, Tuple[bytes, int]]:
    """沙箱內全部檔之寫後（位元組, 權限位）；symlink 記其目標（r1 codex P1-01：只看手列宿主檔會漏其他受管 target）。
    `skip`＝兩側依設計不同之入口與核心位置。"""
    files: Dict[str, Tuple[bytes, int]] = {}
    seen_real: set = set()
    # 追入目錄 symlink（b2 r1 codex P2-03：經目錄 symlink 寫到沙箱外之檔原本不入快照）；記目錄 symlink 本身；
    # 以 realpath 防循環
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        real = os.path.realpath(dirpath)
        if real in seen_real:
            dirnames[:] = []
            continue
        seen_real.add(real)
        dirnames[:] = sorted(d for d in dirnames if d not in _SNAPSHOT_SKIP_DIRS)
        for d in dirnames:
            dp = Path(dirpath) / d
            if dp.is_symlink():
                files[dp.relative_to(root).as_posix() + "/"] = (b"symlink:" + os.readlink(dp).encode("utf-8"), 0)
        for name in sorted(filenames):
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            if rel in skip:
                continue
            if p.is_symlink():
                files[rel] = (b"symlink:" + os.readlink(p).encode("utf-8"), 0)
            elif p.is_file():
                mode = stat.S_IMODE(p.stat().st_mode)
                try:
                    files[rel] = (p.read_bytes(), mode)
                except PermissionError:
                    # 權限位為 0 之檔（C-1 例外④ 行檔）：記「不可讀＋權限位」，兩側同法比對，不崩潰
                    files[rel] = (b"unreadable:", mode)
    return files


def _run(root: Path, argv: List[str], case: Case, env: Dict[str, str]) -> RunOut:
    r = subprocess.run(argv, cwd=str(root / case.cwd), input=case.stdin, capture_output=True, env=env)
    return RunOut(r.returncode, r.stdout, r.stderr, snapshot_tree(root, (case.script_rel, core_rel(case))))


def run_oracle(root: Path, case: Case) -> RunOut:
    """於 oracle 沙箱跑 oracle 入口。"""
    return _run(root, ["bash", case.invoke, *case.args], case,
                _env(root, case.env, case.oracle_env, unset=case.unset_env))


def run_new(root: Path, case: Case) -> RunOut:
    """於新實作沙箱跑新實作（`case.entry`：直呼核心或經入口檔）。"""
    if case.entry == "entry":
        argv = ["bash", case.invoke, *case.args]
    else:
        core = os.path.relpath(root / core_rel(case), root / case.cwd)
        argv = ["python3", core, *case.args]
    return _run(root, argv, case, _env(root, case.env, case.new_env, unset=case.unset_env))


def normalize(out: RunOut, root: Path, other_root: Path) -> RunOut:
    """唯一正規化：把 `root` 路徑字面換成 `other_root`（含 realpath 形）；其他一律不動。"""
    pairs = {str(root): str(other_root), str(root.resolve()): str(other_root.resolve())}

    def sub(b: bytes) -> bytes:
        for src, dst in sorted(pairs.items(), key=lambda kv: -len(kv[0])):
            b = b.replace(src.encode("utf-8"), dst.encode("utf-8"))
        return b

    return RunOut(out.rc, sub(out.stdout), sub(out.stderr), dict(out.files))


def diff(a: RunOut, b: RunOut) -> List[str]:
    """逐位元組比對兩次觀測，回傳差異描述（空＝全等）。"""
    out: List[str] = []
    if a.rc != b.rc:
        out.append(f"rc {a.rc} != {b.rc}")
    for name in ("stdout", "stderr"):
        x, y = getattr(a, name), getattr(b, name)
        if x != y:
            i = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
            out.append(f"{name} 於位元組 {i} 起不同（{len(x)} vs {len(y)}）："
                       f"{x[max(0, i - 40):i + 40]!r} vs {y[max(0, i - 40):i + 40]!r}")
    for rel in sorted(set(a.files) | set(b.files)):
        if rel not in a.files or rel not in b.files:
            out.append(f"file {rel} 只存在於一側")
            continue
        (xa, ma), (xb, mb) = a.files[rel], b.files[rel]
        if xa != xb:
            out.append(f"file {rel} 位元組不同（{len(xa)} vs {len(xb)}）")
        if ma != mb:
            out.append(f"file {rel} 權限位不同（{oct(ma)} vs {oct(mb)}）")
    return out


# SPEC v8 C-1 具名例外⑤：oracle 之 jq 執行期錯誤行（jq 自身印出，輸入檔常為 mktemp 物化暫存檔、措辭為 jq 內部實作）
_JQ_ERROR_LINE = re.compile(rb"^jq: error \(at [^\n]*\): [^\n]*$")


def drop_jq_error_lines(stderr: bytes) -> bytes:
    """只刪**恰符合** `_JQ_ERROR_LINE` 之整行；其餘位元組（含換行）原樣保留。只套用於 oracle 側。"""
    kept = [ln for ln in stderr.split(b"\n") if not _JQ_ERROR_LINE.match(ln)]
    return b"\n".join(kept)


def first_line(stream: bytes) -> str:
    return stream.decode("utf-8", "replace").splitlines()[0] if stream else ""


def expected_first(case: Case, root: Path) -> str:
    """預期首行之 `{root}` 代換為 oracle 沙箱之實體路徑（入口以 `pwd` 取 SCRIPT_DIR，得 realpath）。"""
    return case.expect_first_line.replace("{root}", str(root.resolve()))


def _shared_external_dirs(oroot: Path, nroot: Path) -> List[str]:
    """兩沙箱中目錄 symlink 所指、位於各自根之外且兩側共用之實體目錄（realpath）。"""
    def externals(root: Path) -> set:
        real_root = os.path.realpath(root)
        found = set()
        for dirpath, dirnames, _ in os.walk(root):
            for d in dirnames:
                p = Path(dirpath) / d
                if p.is_symlink():
                    target = os.path.realpath(p)
                    if os.path.isdir(target) and not (target + os.sep).startswith(real_root + os.sep):
                        found.add(target)
        return found
    return sorted(externals(oroot) & externals(nroot))


def check_case(tmp_path: Path, case: Case) -> List[str]:
    """跑一筆語料：先斷言 oracle 命中預期分支，再回傳新舊差異（空＝全等）。"""
    oroot, nroot = make_pair(tmp_path, case)
    shared = _shared_external_dirs(oroot, nroot)
    shared_before = {d: snapshot_tree(Path(d), ()) for d in shared}
    a = run_oracle(oroot, case)
    # 兩沙箱之目錄 symlink 指向同一外部目錄時，oracle 寫入該處會同時出現在新側快照 ⇒ 差分失去鑑別力
    # （b2 r2 codex P2-01）；此類語料一律判不可比、須改為各沙箱獨立之目標
    for d in shared:
        assert snapshot_tree(Path(d), ()) == shared_before[d], (case.case_id, "oracle 寫入兩沙箱共用之外部目錄", d)
    got = first_line(a.stderr if case.expect_rc else a.stdout)
    assert (a.rc, got) == (case.expect_rc, expected_first(case, oroot)), (case.case_id, a.rc, got)
    for rel in case.watch_files:
        assert rel in a.files, (case.case_id, "watch_files 所列宿主檔不在 oracle 寫後快照", rel)
    b = run_new(nroot, case)
    if case.expect_new is not None:
        # C-5 前置例外配對：只准具名訊息不同；stdout、其餘 stderr、rc 與寫後檔案仍全等（r1 codex P2-04）
        named = (expected_first(case, oroot) + "\n").encode("utf-8")
        new_named = (case.expect_new[1] + "\n").encode("utf-8")
        expected = RunOut(case.expect_new[0], a.stdout, a.stderr.replace(named, new_named, 1), a.files)
        return diff(expected, normalize(b, nroot, oroot))
    a = RunOut(a.rc, a.stdout, drop_jq_error_lines(a.stderr), a.files)  # C-1 ⑤：只刪 oracle 側
    diffs = diff(a, normalize(b, nroot, oroot))
    if not diffs:  # 全等即刪兩沙箱（逐筆累積為 GB 級，2026-09-24 佔滿磁碟）；有差異者留供除錯
        for root in (oroot, nroot):
            shutil.rmtree(root, ignore_errors=True)
    return diffs


def exit_catalog() -> Dict[str, str]:
    """由 oracle 原始碼逐一列舉拒絕出口（每個 `return 1`／`_fk_die`／`exit`）→ 標籤：stderr 首行。"""
    from tests.governance import _fkperf_corpus as fc
    return dict(fc.EXIT_CATALOG)


def exit_sites() -> Dict[int, str]:
    """oracle 原始碼中每一條寫 stderr 之行（`>&2` 或 `_fk_die `）之行號 → 歸類：`exit_catalog()` 之出口標籤、
    "continuation"（多行訊息之後續行）、"warning"（不退出之預警首行）、"tool_failure"（oracle 內部 jq／awk／mktemp
    子程序自身失敗之出口，字面合測試之封閉集；新實作無對應分支，不入 catalog）或 "helper"（`_fk_die` 定義行）。逐行手寫歸類，
    須合 `test_fkperf_differential._site_rules` 之機械規則（出口首行不得為續行；r6 codex／grok P1-01），
    供出口清單之獨立完整性錨（`test_exit_sites_cover_every_stderr_line_of_oracle`）。"""
    from tests.governance import _fkperf_corpus as fc
    return dict(fc.EXIT_SITES)


def corpus(kind: str) -> List[Case]:
    """語料五類：real／sandbox／exit／key_order／bytes（SPEC Task 0.1 改法①～⑤）。
    每筆之 `expect_first_line` 為字面：rc≠0 為 stderr 首行、rc=0 為 stdout 首行（空輸出為 ""）。
    `exit` 類每筆以手寫建法構成，不得迴圈轉手 `exit_catalog()` 產生（否則與出口清單之集合比對恆等；r5 grok P1-01）。
    `bytes` 類至少一筆為 `--write` 且以 `watch_files` 列出其寫入之宿主檔（供寫檔結果之差分與鑑別力；r6 grok P1-03）。"""
    from tests.governance import _fkperf_corpus as fc
    return list(fc.CORPUS[kind]())
