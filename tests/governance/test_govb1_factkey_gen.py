"""票 B-25 / Task 2.1 — fact-key 生成器守衛測試。

測什麼：`scripts/gen_fact_key_blocks.sh` 的三種模式（emit／--check／--write）
與其 fail-closed 邊界。通過條件＝下列每條 rc／輸出契約成立。

🔴 本檔的 mutation 是**行為引信**，不是字面比對：
   把生成器複製到 tmp、實際改壞它、再跑一次，看決定性 oracle 是否真的轉紅。
   （字面斷言「原始碼含 LC_ALL=C」同時會產生假綠與假紅——B5 已踩過，見
    handoffs/reconcile/20260809-govb1-b5-review-r2/synth.md。）
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
REG = REPO / "scripts" / "fact_keys.json"
FIX = REPO / "tests" / "governance" / "fixtures" / "govb1"
CLEAN = FIX / "factkey_clean"
DRIFTED = FIX / "factkey_drifted"

KEY = "governance-execution-order"
TARGET_REL = "docs/GOVERNANCE_EXECUTION_ORDER.md"
BEGIN = f"<!-- BEGIN GENERATED: {KEY} -->"
END = f"<!-- END GENERATED: {KEY} -->"


def _run(args, *, cwd: Path = REPO, env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _gen(*args, cwd: Path = REPO, env_extra: dict | None = None):
    return _run([str(GEN), *args], cwd=cwd, env_extra=env_extra)


# --------------------------------------------------------------------------
# 基本存在性與 ASSERT rc 對照（TODO Task 2.1 驗證欄逐條）
# --------------------------------------------------------------------------


def test_generator_and_registry_exist_and_executable():
    assert GEN.is_file(), f"缺生成器 {GEN}"
    assert os.access(GEN, os.X_OK), "生成器須可執行（gov_check 以 [ -x ] 判定）"
    assert REG.is_file(), f"缺註冊表 {REG}"


AMENDMENT = REPO / "docs" / "GOV_B25_SCOPE_AMENDMENT.md"


def _amendment_keys():
    """讀延伸檔 §2 之機械 SoT。缺檔／重複項一律 fail-closed（條件⑥）。"""
    assert AMENDMENT.is_file(), (
        f"缺延伸檔 {AMENDMENT}：凍結宣告之偏離無登記處 → fail-closed"
    )
    frozen, added = [], []
    for line in AMENDMENT.read_text(encoding="utf-8").splitlines():
        if line.startswith("FACTKEY-FROZEN: "):
            frozen.append(line[len("FACTKEY-FROZEN: "):].strip())
        elif line.startswith("FACTKEY-ADDED: "):
            added.append(line[len("FACTKEY-ADDED: "):].strip())
    assert frozen, "延伸檔缺 FACTKEY-FROZEN 宣告 → fail-closed"
    assert added, "延伸檔缺 FACTKEY-ADDED 宣告 → fail-closed"
    assert len(frozen) == len(set(frozen)), f"FACTKEY-FROZEN 含重複項: {frozen}"
    assert len(added) == len(set(added)), f"FACTKEY-ADDED 含重複項: {added}"
    assert not (set(frozen) & set(added)), "FROZEN 與 ADDED 不得交集"
    return set(frozen), set(added)


def test_registry_key_set_equals_amendment_declaration():
    """票 B-25 站 2.5 Task 1.4（原 TODO 實作要點 1 之延伸；偏離登記見 docs/GOV_B25_SCOPE_AMENDMENT.md）。

    🔴 三條**集合相等**（禁 issubset/>=/in）：
      ① registry 全集 == FROZEN ∪ ADDED
      ② ADDED == _schema.status_keys（r3 CODEX-R3-P1-04：破解自我循環——
         單靠①時延伸檔漏列一個 key，三方仍互相一致而無人轉紅）
      ③ 凍結期單一 key 仍須在 FROZEN 內
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    fact_keys = {k for k in data if k != "_schema"}
    frozen, added = _amendment_keys()

    assert fact_keys == frozen | added, (
        f"registry key 集合與延伸檔宣告不符：registry={sorted(fact_keys)} "
        f"vs 宣告={sorted(frozen | added)}"
    )
    assert KEY in frozen, f"凍結期單一 key {KEY} 未列於 FACTKEY-FROZEN"

    status_keys = set(data["_schema"]["status_keys"])
    assert added == status_keys, (
        "🔴 延伸檔 ADDED 與 _schema.status_keys 不相等 ⇒ 可能漏交或多交狀態 key："
        f"ADDED={sorted(added)} vs status_keys={sorted(status_keys)}"
    )

    # 每個 key 的結構仍須合法
    for k in fact_keys:
        tgt = data[k]["target"]
        assert isinstance(tgt, (str, list))
        if isinstance(tgt, list):
            assert tgt and all(isinstance(t, str) for t in tgt)
            assert len(tgt) == len(set(tgt)), f"{k} 之 target 含重複路徑"
        rows = data[k]["rows"]
        assert rows and all(
            isinstance(r, list) and all(isinstance(c, str) for c in r) for r in rows
        )
    assert TARGET_REL in (
        data[KEY]["target"] if isinstance(data[KEY]["target"], list) else [data[KEY]["target"]]
    )


def test_t21_assert_clean_fixture_rc_zero():
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=...factkey_clean THEN rc=0"""
    r = _gen("--check", env_extra={"GOVB1_FACTKEY_ROOT": str(CLEAN)})
    assert r.returncode == 0, f"clean fixture 應 rc=0，實得 {r.returncode}\n{r.stderr}"


def test_t21_assert_drifted_fixture_rc_nonzero_with_key_and_file():
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=...factkey_drifted THEN rc!=0

    邊界②要求訊息含檔名與 key——否則 push 被擋時無從得知該修哪一份。
    """
    r = _gen("--check", env_extra={"GOVB1_FACTKEY_ROOT": str(DRIFTED)})
    assert r.returncode != 0, "drifted fixture 應 rc≠0（漂移未被偵測＝機制失效）"
    assert KEY in r.stderr, f"訊息須含 key，實得: {r.stderr}"
    assert TARGET_REL in r.stderr, f"訊息須含檔名，實得: {r.stderr}"


def test_real_repo_check_passes():
    """真實 repo 必須自洽——否則 Task 2.2 掛上去會把每一次 push 擋死。"""
    r = _gen("--check")
    assert r.returncode == 0, f"repo 根 --check 應 rc=0，實得 {r.returncode}\n{r.stderr}"


# --------------------------------------------------------------------------
# T-2.1-D1 決定性
# --------------------------------------------------------------------------


def test_t21_d1_deterministic_three_runs_identical():
    outs = [_gen().stdout for _ in range(3)]
    assert outs[0] == outs[1] == outs[2], "連跑 3 次輸出不同 ⇒ 機制退化為噪音"
    assert outs[0].strip(), "輸出不得為空"


def test_output_has_no_bom_no_crlf_no_timestamp():
    raw = subprocess.run(
        ["bash", str(GEN)], cwd=str(REPO), capture_output=True
    ).stdout
    assert not raw.startswith(b"\xef\xbb\xbf"), "輸出不得含 BOM"
    assert b"\r\n" not in raw, "輸出須全程 LF"
    # 時間戳會使 diff 恆紅：任何 4 位年份樣式皆視為違規訊號
    text = raw.decode("utf-8")
    import re

    assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text), (
        f"輸出疑似含時間戳:\n{text}"
    )


def test_generator_runs_under_two_seconds():
    t0 = time.monotonic()
    _gen()
    elapsed = time.monotonic() - t0
    assert elapsed < 2.0, f"生成器單次須 <2s，實測 {elapsed:.2f}s"


# --------------------------------------------------------------------------
# tmp 沙箱：可任意改壞的生成器副本
# --------------------------------------------------------------------------

# C 與 UTF-8 collation 對這三列的排序不同（本機實測：
#   LC_ALL=C          → B-x _z a-y
#   LC_ALL=en_US.UTF-8 → _z a-y B-x）
_LOCALE_PROBE_ROWS = [["a-y", "x"], ["B-x", "x"], ["_z", "x"]]

# 🔴 mutation 錨點須**唯一指向 `_fk_gen_block` 的排序**。
#   出生事故（票 B-25 站 2.5 Task 1.1，2026-08-10）：新增 `_fk_targets`／`_fk_all_targets`
#   後，生產檔出現三處 `| LC_ALL=C sort`，而 `_mutate` 用 `replace(..., 1)` 只改第一處
#   ⇒ 兩條 mutation 打到「去重排序」而非「生成排序」，**測試轉紅但原因是錨點失準**。
#   修法＝把錨點收窄到只有 `_fk_gen_block` 具備的前綴（含 `"${REG}"`）。
#   這是**加嚴**（更精確的定位），不是放寬。
_ROWS_SORT_ANCHOR = '"${REG}" | LC_ALL=C sort'


def _sandbox(tmp_path: Path, registry: dict, *, inject_schema: bool = True) -> Path:
    """把生成器與一份自訂註冊表複製到 tmp；回傳該 scripts 目錄。

    🔴 票 B-25 站 2.5 Task 1.2：註冊表有 ≥1 fact-key 時，`_schema` 四欄為必要且 fail-closed。
    本 helper 預設注入一份**最小合法** `_schema`，使既有測試仍測其原本標的
    （sort/locale/marker/target 等），而非全部被 schema 檢查攔在前面。
    要測「四欄缺席即 fail-closed」者傳 `inject_schema=False`（見 test_schema_sets_*）。
    無 fact-key（空註冊表）時不注入——`test_empty_registry_is_rc_zero_not_failure` 契約不變。
    """
    fact_keys = [k for k in registry if k != "_schema"]
    if inject_schema and fact_keys and "_schema" not in registry:
        registry = {
            "_schema": {
                "status_enum": ["✅"],
                "status_keys": fact_keys,
                "status_scope": ["docs/"],
                "status_scope_grandfathered": ["docs/__none__.md"],
            },
            **registry,
        }
    sdir = tmp_path / "scripts"
    sdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEN, sdir / GEN.name)
    (sdir / "fact_keys.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return sdir


def _mkroot(tmp_path: Path, name: str = "root") -> Path:
    """建立一個 tmp 宿主根，並 `git init`。

    🔴 票 B-25 站 2.5 Task 2.1 邊界⑥：偵測器要求 root 為 git 工作樹，否則 fail-closed
    （不得靜默退回「只掃 target」）。三個候選解中採 (a)——在 helper 內 git init，
    保留 fail-closed 契約；(b) 空 status_scope 與 Task 1.2 衝突、(c) 依環境變數跳過＝靜默旁路。
    非 git 樹之 fail-closed 另有專測 `test_t21_non_git_root_is_fail_closed`。
    """
    root = tmp_path / name
    (root / "docs").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    return root


def _mutate(sdir: Path, old: str, new: str) -> None:
    p = sdir / GEN.name
    src = p.read_text(encoding="utf-8")
    # 🔴 訊息須指向真正的病〔COMPOSER-R1-P2-01〕：若生產檔已失去 locale 釘子，
    #    原訊息只說「測試脫節」，委員會據此會往「測試壞了」的方向查——反了。
    assert old in src, (
        f"mutation 目標字串不存在: {old!r}\n"
        "若目標是 `| LC_ALL=C sort`，代表**生產檔已失去 locale 釘子**——"
        "那正是 T-2.1-M1 要防的回歸，不是測試脫節。"
    )
    p.write_text(src.replace(old, new, 1), encoding="utf-8")


def _discriminating_locale() -> str | None:
    """找一個與 C 排序結果不同的 locale；找不到回 None。"""
    probe = "a-y\nB-x\n_z\n"
    base = subprocess.run(
        ["sort"], input=probe, capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},
    ).stdout
    for cand in ("en_US.UTF-8", "en_US.utf8", "C.UTF-8", "en_GB.UTF-8"):
        got = subprocess.run(
            ["sort"], input=probe, capture_output=True, text=True,
            env={**os.environ, "LC_ALL": cand},
        )
        if got.returncode == 0 and got.stdout != base:
            return cand
    return None


# --------------------------------------------------------------------------
# T-2.1-M1 — 排序改為未指定 locale ⇒ 決定性測試轉紅（行為引信）
# --------------------------------------------------------------------------


def test_t21_m1a_sort_is_load_bearing(tmp_path):
    """環境無關的引信：拿掉排序即輸出改變 ⇒ 證明 `sort` 真的承重。

    註冊表 rows 刻意亂序；有排序 ⇒ 輸出照序數，無排序 ⇒ 照 JSON 原序。
    """
    reg = {"k": {"target": "t.md", "rows": [["030", "c"], ["010", "a"], ["020", "b"]]}}
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, _ROWS_SORT_ANCHOR, '"${REG}" | cat')

    out_good = _run([str(good / GEN.name)]).stdout
    out_bad = _run([str(bad / GEN.name)]).stdout
    assert out_good != out_bad, "拿掉排序輸出未變 ⇒ 這條 mutation 是空心的"
    assert out_good.splitlines()[1].startswith("010"), out_good


def test_t21_m1b_locale_pin_removal_breaks_determinism(tmp_path):
    """TODO 指定之 mutation：把排序改為未指定 locale ⇒ 決定性 oracle 轉紅。

    判準＝同一支腳本在兩種環境 locale 下輸出是否一致。
    釘住版：一致（綠）。拿掉釘子：不一致（紅）⇒ 證明釘子承重。
    """
    loc = _discriminating_locale()
    if loc is None:
        # 🔴 **不得 skip**〔CODEX-R1-P1-04／COMPOSER-R1-P2-01〕：
        #    靜默 skip 會讓 locale 貧瘠的 runner（CI）完全不驗這條 mutation ⇒ fail-open。
        #    退化成較弱但**仍有 oracle** 的來源檢查：釘子必須在。
        #    m1a 只證「sort 承重」，不證「locale 已釘」——兩者不可互相頂替。
        assert _ROWS_SORT_ANCHOR in GEN.read_text(encoding="utf-8"), (
            f"本機無差異 locale 且生產檔已無 `{_ROWS_SORT_ANCHOR}` ⇒ 決定性契約失守"
        )
        return

    reg = {"k": {"target": "t.md", "rows": _LOCALE_PROBE_ROWS}}
    pinned = _sandbox(tmp_path / "pinned", reg)
    unpinned = _sandbox(tmp_path / "unpinned", reg)
    _mutate(unpinned, _ROWS_SORT_ANCHOR, '"${REG}" | sort')

    def out(sdir: Path, lc: str) -> str:
        return _run([str(sdir / GEN.name)], env_extra={"LC_ALL": lc}).stdout

    assert out(pinned, "C") == out(pinned, loc), (
        "釘住 LC_ALL=C 後輸出仍隨環境改變 ⇒ 決定性契約未成立"
    )
    assert out(unpinned, "C") != out(unpinned, loc), (
        f"拿掉 LC_ALL=C 後輸出未隨 {loc} 改變 ⇒ 這條 mutation 是空心的"
    )


def test_t21_m1c_generation_failure_is_not_swallowed(tmp_path):
    """🔴 CODEX-R1-P1-03 回歸：生成器**自己失敗**時 `--check` 不得回 0。

    病：`_fk_gen_block` 最後一行是 printf ⇒ 函式 rc 恆 0；`--check` 又只比字串，
    於是「jq/sort 掛了但輸出恰好相符」＝靜默通過。
    引信：讓副本的 `_fk_gen_block` **輸出正確 block 之後 return 1**。
    """
    root = _mkroot(tmp_path)
    reg = {"k": {"target": "docs/t.md", "rows": [["010", "a"]]}}
    sdir = _sandbox(tmp_path, reg)
    env = {"GOVB1_FACTKEY_ROOT": str(root)}

    # 先產生一份與註冊表一致的宿主檔（此時 --check 應綠）
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n", encoding="utf-8"
    )
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode == 0

    _mutate(sdir, "  printf '<!-- END GENERATED: %s -->\\n' \"$1\" || return 1",
            "  printf '<!-- END GENERATED: %s -->\\n' \"$1\"\n  return 1")
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode != 0, "生成器失敗卻放行 ⇒ --check 只比字串、不驗生成成功"
    assert "GEN FAILED" in r.stderr, r.stderr


def test_unregistered_generated_block_is_rejected(tmp_path):
    """🔴 CODEX-R1-P1-02 回歸：宿主檔內出現未登記的 generated block ⇒ 拒。

    那種區塊長得像機械產物、讀者會當成權威，但註冊表不知道它 ⇒ 永遠不會被比對。
    """
    root = _mkroot(tmp_path)
    reg = {"k": {"target": "docs/t.md", "rows": [["010", "a"]]}}
    sdir = _sandbox(tmp_path, reg)
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    tgt = root / "docs" / "t.md"
    tgt.write_text("<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n", encoding="utf-8")
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode == 0

    tgt.write_text(
        tgt.read_text(encoding="utf-8")
        + "\n<!-- BEGIN GENERATED: totally-made-up -->\n偽造的權威表\n"
          "<!-- END GENERATED: totally-made-up -->\n",
        encoding="utf-8",
    )
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode != 0, "未登記的 generated block 竟被放行"
    assert "UNREGISTERED BLOCK" in r.stderr and "totally-made-up" in r.stderr


# --------------------------------------------------------------------------
# fail-closed 邊界
# --------------------------------------------------------------------------


def test_empty_registry_is_rc_zero_not_failure(tmp_path):
    """邊界①：註冊表為空物件 ⇒ rc=0（無事可做，不得 fail）。"""
    sdir = _sandbox(tmp_path, {})
    for args in ([], ["--check"]):
        r = _run([str(sdir / GEN.name), *args])
        assert r.returncode == 0, f"空註冊表 {args} 應 rc=0，實得 {r.returncode}\n{r.stderr}"


def test_missing_registry_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {})
    (sdir / "fact_keys.json").unlink()
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


def test_malformed_registry_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {})
    (sdir / "fact_keys.json").write_text("[1,2,3]", encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


@pytest.mark.parametrize(
    "badkey",
    ["Governance-Order", "with space", "under_score", "-leading", "中文鍵"],
)
def test_illegal_key_name_is_fail_closed(tmp_path, badkey):
    """key 字元集合是安全前提：它會被嵌進 grep/sed 正則。"""
    sdir = _sandbox(tmp_path / badkey.replace(" ", "_"), {badkey: {"target": "t.md", "rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"非法 key {badkey!r} 應 fail-closed"
    assert "fail-closed" in r.stderr


def test_reserved_schema_key_is_skipped_not_treated_as_fact_key(tmp_path):
    sdir = _sandbox(tmp_path, {"_schema": {"about": "doc"}})
    r = _run([str(sdir / GEN.name)])
    assert r.returncode == 0, r.stderr
    assert r.stdout == "", "保留鍵不得產生 block"


@pytest.mark.parametrize("bad_target", ["/etc/passwd", "../outside.md", "a/../../b.md"])
def test_target_path_escape_is_fail_closed(tmp_path, bad_target):
    sdir = _sandbox(tmp_path / bad_target.replace("/", "_"), {"k": {"target": bad_target, "rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"target {bad_target!r} 應被拒"


def test_missing_target_key_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {"k": {"rows": []}})
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0 and "fail-closed" in r.stderr


@pytest.mark.parametrize("bad_rows", [{"rows": "notalist"}, {"rows": [["a"], "b"]}, {"rows": [[1]]}])
def test_rows_type_violation_is_fail_closed(tmp_path, bad_rows):
    reg = {"k": {"target": "t.md", **bad_rows}}
    sdir = _sandbox(tmp_path / str(abs(hash(str(bad_rows)))), reg)
    r = _run([str(sdir / GEN.name), "--check"])
    assert r.returncode != 0, f"rows={bad_rows!r} 應 fail-closed"


def test_missing_target_file_is_fail_closed(tmp_path):
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/nope.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], cwd=tmp_path)
    assert r.returncode != 0
    assert "MISSING TARGET" in r.stderr and "docs/nope.md" in r.stderr


def test_no_marker_is_fail_closed_not_silent_pass(tmp_path):
    """🔴 TODO 邊界②：宿主檔缺邊界標記 ⇒ rc≠0（本條若失守，機制形同關閉）。"""
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text("沒有任何標記\n", encoding="utf-8")
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "缺標記竟放行 ⇒ fail-open"
    assert "MARKER" in r.stderr and "docs/t.md" in r.stderr


def test_duplicate_markers_are_fail_closed(tmp_path):
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n"
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n",
        encoding="utf-8",
    )
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0 and "MARKER" in r.stderr


def test_write_refuses_when_markers_absent(tmp_path):
    """--write 不得憑空追加：位置不明的寫入比不寫更危險。"""
    root = _mkroot(tmp_path)
    tgt = root / "docs" / "t.md"
    tgt.write_text("原文\n", encoding="utf-8")
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["1", "a"]]}})
    r = _run([str(sdir / GEN.name), "--write"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0
    assert tgt.read_text(encoding="utf-8") == "原文\n", "被拒時不得留下任何修改"


def test_write_then_check_round_trip(tmp_path):
    root = _mkroot(tmp_path)
    tgt = root / "docs" / "t.md"
    tgt.write_text(
        "前言\n<!-- BEGIN GENERATED: k -->\n舊內容\n<!-- END GENERATED: k -->\n後記\n",
        encoding="utf-8",
    )
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "rows": [["020", "b"], ["010", "a"]]}})
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode != 0
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode == 0
    body = tgt.read_text(encoding="utf-8")
    assert body.startswith("前言\n") and body.endswith("後記\n"), "標記外的內容不得被動到"
    assert "舊內容" not in body
    assert body.index("010\ta") < body.index("020\tb")


@pytest.mark.parametrize("args", [["--bogus"], ["--check", "--write"], ["check"]])
def test_unknown_or_extra_args_are_fail_closed(args):
    r = _gen(*args)
    assert r.returncode == 2, f"{args} 應 rc=2，實得 {r.returncode}\n{r.stderr}"


def test_fixtures_differ_only_in_block_content():
    """正反 fixture 的鑑別力來源必須是「block 內容」，不是「有沒有標記」。"""
    c = (CLEAN / TARGET_REL).read_text(encoding="utf-8").splitlines()
    d = (DRIFTED / TARGET_REL).read_text(encoding="utf-8").splitlines()
    assert len(c) == len(d), "兩份 fixture 列數不同 ⇒ 對照失去鑑別力"
    assert BEGIN in c and END in c and BEGIN in d and END in d
    diff = [i for i, (a, b) in enumerate(zip(c, d)) if a != b]
    assert len(diff) == 1, f"drifted 應恰一列不同，實得 {len(diff)} 列"


# ==========================================================================
# 票 B-25 站 2.5（docs/GOVB25_STATUS_FACTKEY_SPEC.md r5）
# ==========================================================================

import subprocess as _sp

_BATCH_KEY = "governance-batch-status"
_TICKET_KEY = "governance-ticket-closure"

# SPEC §E 之票號 token 抽取器（絕對位移版）。
# 🔴 此處**內嵌**而非獨立腳本：新增 scripts/ 檔不在 govb1_scope.manifest allow 內會撞 G-7。
#    具名偏離見 docs/GOV_B25_SCOPE_AMENDMENT.md §4。
_TOK_AWK = r'''
  function boundary_ok(s, st, len,   pre, post) {
    pre  = (st == 1) ? "" : substr(s, st - 1, 1)
    post = substr(s, st + len, 1)
    if (pre  ~ /[0-9A-Za-z_-]/) return 0
    if (post ~ /[0-9A-Za-z_-]/) return 0
    return 1 }
  function scan(s, re,   off, rest, st, tok) {
    off = 0; rest = s
    while (match(rest, re)) {
      st  = off + RSTART
      tok = substr(s, st, RLENGTH)
      if (boundary_ok(s, st, RLENGTH)) print substr(tok, index(tok, "B"))
      off  = st + RLENGTH - 1
      rest = substr(s, off + 1) } }
  { scan($0, "票 B-[0-9]+"); scan($0, "B3R") }
'''


def _tok(text: str) -> list[str]:
    r = _sp.run(["awk", _TOK_AWK], input=text, capture_output=True, text=True,
                env={**os.environ, "LC_ALL": "C"})
    assert r.returncode == 0, r.stderr
    return [x for x in r.stdout.splitlines() if x]


def _section(path: Path, start_re: str, stop_re: str) -> str:
    r = _sp.run(["awk", f'/{start_re}/{{f=1;next}} f&&/{stop_re}/{{exit}} f', str(path)],
                capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    assert r.returncode == 0, r.stderr
    return r.stdout


def _rows(key: str) -> list[list[str]]:
    return json.loads(REG.read_text(encoding="utf-8"))[key]["rows"]


# --- Task 1.1 多宿主 ＋ projection oracle ---------------------------------

def _multi_root(tmp_path: Path, a_body: str, b_body: str) -> tuple[Path, Path]:
    reg = {"k": {"target": ["docs/a.md", "docs/b.md"], "rows": [["010", "x"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(a_body, encoding="utf-8")
    (root / "docs" / "b.md").write_text(b_body, encoding="utf-8")
    return sdir, root


_BLK_OK = "<!-- BEGIN GENERATED: k -->\n010\tx\n<!-- END GENERATED: k -->\n"
_BLK_BAD = "<!-- BEGIN GENERATED: k -->\n010\ty\n<!-- END GENERATED: k -->\n"


def test_t11_multi_target_clean_rc_zero(tmp_path):
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=<多宿主 clean> THEN rc=0"""
    sdir, root = _multi_root(tmp_path, _BLK_OK, _BLK_OK)
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode == 0, r.stderr


def test_t11_second_host_drift_is_caught_and_named(tmp_path):
    """ASSERT --check WHEN GOVB1_FACTKEY_ROOT=<僅第二宿主漂移> THEN rc!=0

    🔴 M1 承重：若多宿主迴圈只處理第一筆，本測試轉綠 ⇒ 機制失效。
    訊息須含**第二宿主檔路徑**，否則「擋下了但說不出改哪份」。
    """
    sdir, root = _multi_root(tmp_path, _BLK_OK, _BLK_BAD)
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0
    assert "docs/b.md" in r.stderr, r.stderr


def test_t11_projection_oracle_two_hosts_self_consistent_but_different(tmp_path):
    """ASSERT --check WHEN 兩宿主各自自洽但彼此不同 THEN rc!=0（projection oracle 承重）"""
    sdir, root = _multi_root(tmp_path, _BLK_OK, _BLK_BAD)
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "同一 key 之兩投影不同卻通過 ⇒ oracle 空心"


@pytest.mark.parametrize("bad_target", [[], ["docs/a.md", "docs/a.md"], ["/abs.md"], ["../x.md"], [1]])
def test_t11_target_array_edge_cases_are_fail_closed(tmp_path, bad_target):
    reg = {"k": {"target": bad_target, "rows": [["010", "x"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(_BLK_OK, encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, f"target={bad_target} 應 fail-closed"


# --- Task 1.2 schema 四項封閉集合 ------------------------------------------

@pytest.mark.parametrize("drop", ["status_enum", "status_keys", "status_scope",
                                  "status_scope_grandfathered"])
def test_t12_schema_set_absent_is_fail_closed(tmp_path, drop):
    """ASSERT --check WHEN registry_<欄>=absent THEN rc!=0"""
    reg = {
        "_schema": {"status_enum": ["✅"], "status_keys": ["k"],
                    "status_scope": ["docs/"], "status_scope_grandfathered": ["docs/n.md"]},
        "k": {"target": "docs/a.md", "rows": [["010", "x"]]},
    }
    del reg["_schema"][drop]
    sdir = _sandbox(tmp_path, reg, inject_schema=False)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(_BLK_OK, encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, f"_schema.{drop} 缺席卻通過 ⇒ fail-open"
    assert drop in r.stderr


def test_t12_status_keys_containing_unregistered_key_is_fail_closed(tmp_path):
    """ASSERT --check WHEN registry_status_keys_contains_unregistered THEN rc!=0"""
    reg = {
        "_schema": {"status_enum": ["✅"], "status_keys": ["k", "nope"],
                    "status_scope": ["docs/"], "status_scope_grandfathered": ["docs/n.md"]},
        "k": {"target": "docs/a.md", "rows": [["010", "x"]]},
    }
    sdir = _sandbox(tmp_path, reg, inject_schema=False)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(_BLK_OK, encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0
    assert "nope" in r.stderr


@pytest.mark.parametrize("scope", ["docs/*", "docs/?.md", "docs/[ab].md"])
def test_t12_status_scope_wildcard_is_fail_closed(tmp_path, scope):
    """r3 CODEX-R3-P1-02：prefix 原樣當 pathspec 無決定性語意 ⇒ 禁 wildcard。"""
    reg = {
        "_schema": {"status_enum": ["✅"], "status_keys": ["k"],
                    "status_scope": [scope], "status_scope_grandfathered": ["docs/n.md"]},
        "k": {"target": "docs/a.md", "rows": [["010", "x"]]},
    }
    sdir = _sandbox(tmp_path, reg, inject_schema=False)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(_BLK_OK, encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, f"status_scope={scope} 含 wildcard 卻通過"


def test_t12_empty_registry_still_rc_zero_after_schema_gate(tmp_path):
    """🔴 r5 CODEX-R5-P1-02：新增 fail-closed 不得與「空註冊表 rc=0」契約衝突。"""
    sdir = _sandbox(tmp_path, {}, inject_schema=False)
    r = _run([str(sdir / GEN.name), "--check"],
             env_extra={"GOVB1_FACTKEY_ROOT": str(tmp_path)})
    assert r.returncode == 0, f"空註冊表應 rc=0，實得 {r.returncode}\n{r.stderr}"


# --- Task 1.3 §E 識別碼機械導出 vs key rows -------------------------------

def test_e3_ticket_union_matches_key_rows():
    """SPEC §E3：union（HANDOFF 活缺口 ∪ backlog scope 缺口子節）恰等於 ticket key 之票欄。"""
    op1 = _section(REPO / "HANDOFF.md", r"^## 🔴 未修的活缺口", r"^## ")
    op2 = _section(REPO / "handoffs" / "20260801-GOV-AMEND-BACKLOG.md",
                   r"^### 🔴 2026-08-10 scope 缺口", r"^### ")
    union = sorted(set(_tok(op1)) | set(_tok(op2)))
    rows = sorted({r[1] for r in _rows(_TICKET_KEY)})
    assert union == rows, f"E3 union={union} 與 key rows={rows} 不符（第三方可重跑）"


def test_e1_e2_batch_ids_match_key_rows():
    """SPEC §E1／§E2：第 0 批（GOVB0 TODO §B 表）＋ B3R ＋ 第 1 批（W′ TSV）。"""
    b0 = _sp.run(
        ["awk", '/^## §B 批次執行策略/{f=1;next} f&&/^## /{exit} f',
         str(REPO / "docs" / "GOVB0_FRICTION_TODO.md")],
        capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"}).stdout
    import re as _re
    ids0 = {m for line in b0.splitlines()
            for m in _re.findall(r"^\| \*\*(B[0-9]+)\*\*", line)}
    assert (REPO / "docs" / "GOVB0_B3R_LEXER_SPEC.md").is_file()
    ids0.add("B3R")
    tsv = (REPO / "scripts" / "govb1_task_tickets.tsv").read_text(encoding="utf-8")
    ids1 = {"b" + line.split("\t")[0] for line in tsv.splitlines()[1:]
            if line and line.split("\t")[0].isdigit()}
    rows = {r[1] for r in _rows(_BATCH_KEY)}
    assert ids0 | ids1 == rows, f"E1∪E2={sorted(ids0 | ids1)} 與 key rows={sorted(rows)} 不符"


def test_status_values_are_all_in_status_enum():
    enum = set(json.loads(REG.read_text(encoding="utf-8"))["_schema"]["status_enum"])
    for key, col in ((_BATCH_KEY, 2), (_TICKET_KEY, 2)):
        for r in _rows(key):
            assert r[col] in enum, f"{key} 之狀態值 {r[col]!r} 不在 status_enum"


# --- Task 1.3 票號 token 邊界 TP/TN 矩陣（SPEC §E，13 列）------------------

@pytest.mark.parametrize("text,expected", [
    ("票 B-15", ["B-15"]),
    ("票 B-15、票 B-31", ["B-15", "B-31"]),
    ("票 B-53）落地前", ["B-53"]),
    ("（B3R）", ["B3R"]),
    ("票 B-99foo", []),
    ("XB3R", []),
    ("B3RISH", []),
    ("B3R-lexer", []),
    ("GOVB0 B4", []),
    ("R-15", []),
    ("CODEX-R8-P1-03", []),
    ("B3RB3R", []),
    ("XB3RB3R", []),
])
def test_ticket_token_boundary_matrix(text, expected):
    """r3 CODEX-R3-P1-01 ＋ r4 CODEX-R4-P1-01：末兩列為 sliced-context 反例。"""
    assert _tok(text) == expected, f"輸入 {text!r}"


# --- Task 2.1 手寫狀態偵測器 --------------------------------------------

def _detector_case(tmp_path: Path, *, body: str, other_name: str = "other.md",
                   track: bool = True, grandfathered=None):
    reg = {"k": {"target": "docs/a.md", "rows": [["010", "ZZID"]]}}
    if grandfathered is not None:
        reg = {
            "_schema": {"status_enum": ["✅"], "status_keys": ["k"],
                        "status_scope": ["docs/"],
                        "status_scope_grandfathered": grandfathered},
            **reg,
        }
        sdir = _sandbox(tmp_path, reg, inject_schema=False)
    else:
        sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n010\tZZID\n<!-- END GENERATED: k -->\n",
        encoding="utf-8")
    (root / "docs" / other_name).write_text(body, encoding="utf-8")
    if track:
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    return _run([str(sdir / GEN.name), "--check"],
                env_extra={"GOVB1_FACTKEY_ROOT": str(root)})


def test_t21_handwritten_status_in_tracked_file_is_rejected(tmp_path):
    """ASSERT --check WHEN 範圍內已追蹤檔於區塊外手寫一行狀態 THEN rc!=0"""
    r = _detector_case(tmp_path, body="批次 ZZID 目前 ✅ 了\n")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "HANDWRITTEN" in r.stderr and "ZZID" in r.stderr


def test_t21_handwritten_status_in_untracked_file_is_rejected(tmp_path):
    """ASSERT --check WHEN 範圍內**未追蹤**檔於區塊外手寫一行狀態 THEN rc!=0

    🔴 r2 CODEX-R2-P1-01／COMPOSER-R2-P1-03 之承重測試：
    列舉器若只用 `git ls-files`（不帶 --others），本測試轉綠 ⇒ 旁路重開。
    """
    r = _detector_case(tmp_path, body="批次 ZZID 目前 ✅ 了\n", track=False)
    assert r.returncode != 0, "未追蹤檔的手寫狀態未被偵測 ⇒ r2 旁路重現"
    assert "ZZID" in r.stderr


def _legal_block_case(tmp_path: Path, *, outside: bool):
    """同一段「識別碼＋狀態值」文字，置於**合法**生成區塊內 vs 區塊外之對照。

    🔴 r6 CODEX-R6-P1-02 指出前版此測試只斷言「無 HANDWRITTEN」而未斷言 rc==0，
    是空心的；且其構造用的是**未登記** key，現已改為 fake-block 而被拒。
    本版改用 registry 自身之合法區塊內容（rows 第 3 欄即狀態值），對照組才有鑑別力。
    """
    reg = {"k": {"target": "docs/a.md", "rows": [["010", "ZZID", "✅"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    blk = "<!-- BEGIN GENERATED: k -->\n010\tZZID\t✅\n<!-- END GENERATED: k -->\n"
    (root / "docs" / "a.md").write_text(blk, encoding="utf-8")
    if outside:
        (root / "docs" / "a.md").write_text(blk + "010\tZZID\t✅\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    return _run([str(sdir / GEN.name), "--check"],
                env_extra={"GOVB1_FACTKEY_ROOT": str(root)})


def test_t21_same_text_inside_legal_block_is_rc_zero():
    """對照組上半：合法區塊**內**之同一段文字 ⇒ rc=0（見下一條的對照）。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = _legal_block_case(Path(td), outside=False)
    assert r.returncode == 0, f"合法區塊內不應被擋，實得 {r.returncode}\n{r.stderr}"


def test_t21_same_text_outside_block_is_rejected():
    """對照組下半：同一段文字移到區塊**外** ⇒ rc!=0。

    兩條合起來證明鑑別力來源是「在不在區塊外」，不是「檔案裡有沒有這些字」。
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        r = _legal_block_case(Path(td), outside=True)
    assert r.returncode != 0, "區塊外之同一段文字未被擋 ⇒ 鑑別力空心"
    assert "HANDWRITTEN" in r.stderr


def test_t21_fake_generated_block_in_non_host_file_is_rejected(tmp_path):
    """🔴 r6 CODEX-R6-P1-02 之承重測試：非宿主檔貼假 `BEGIN GENERATED` 藏狀態。

    codex 實跑反例：`docs/other.md` 內放一組未登記之 BEGIN/END 與 `ZZID ✅`，
    前版偵測器把任何 marker block 當成區塊內而跳過 ⇒ rc=0，可構造之 fail-open。
    """
    r = _detector_case(
        tmp_path,
        body="<!-- BEGIN GENERATED: zz -->\n批次 ZZID 目前 ✅ 了\n<!-- END GENERATED: zz -->\n",
        other_name="other.md")
    assert r.returncode != 0, "假生成區塊未被拒 ⇒ r6 旁路重現"
    assert "FAKE BLOCK" in r.stderr or "HANDWRITTEN" in r.stderr, r.stderr


def test_t21_newline_in_filename_does_not_evade_scan(tmp_path):
    """🔴 r6 CODEX-R6-P1-03 之承重測試：含換行之檔名。

    codex 實跑反例：`docs/hidden<LF>name.md` 內含 `ZZID ✅`，
    前版未帶 `-z` 之逐行解析會把該路徑切碎而漏掃 ⇒ rc=0。
    """
    reg = {"k": {"target": "docs/a.md", "rows": [["010", "ZZID"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n010\tZZID\n<!-- END GENERATED: k -->\n",
        encoding="utf-8")
    (root / "docs" / "hidden\nname.md").write_text("批次 ZZID 目前 ✅ 了\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "含換行檔名之手寫狀態未被偵測 ⇒ r6 旁路重現"
    assert "ZZID" in r.stderr


def test_t21_identifier_and_status_on_separate_lines_not_triggered(tmp_path):
    """具名偵測邊界（SPEC Task 2.1 邊界①）：兩者分處兩行 ⇒ 不觸發。"""
    r = _detector_case(tmp_path, body="批次 ZZID\n目前 ✅ 了\n")
    assert "HANDWRITTEN" not in r.stderr, r.stderr


def test_t21_grandfathered_list_is_locked_by_set_equality():
    """🔴 豁免清單以集合相等鎖死 ⇒ 新增檔案無法靜默加入豁免。

    本測試即該「集合相等」之機械載體：改 registry 的豁免清單而不改本表即轉紅。
    """
    expected = {
        "白話說明/README.md",
        "白話說明/流程摩擦記錄.md",
        "白話說明/治理進度日誌.md",
        "白話說明/第0批-在做什麼.md",
        "白話說明/第0批-施工清單.md",
        "白話說明/第1批-在做什麼.md",
        "白話說明/第1批-施工清單.md",
    }
    got = set(json.loads(REG.read_text(encoding="utf-8"))
              ["_schema"]["status_scope_grandfathered"])
    assert got == expected, (
        f"豁免清單與本表不相等：多={sorted(got - expected)} 少={sorted(expected - got)}。"
        "新增豁免須同時修訂本表並經審查——這正是「不得靜默加入豁免」的機械強制點。"
    )


def test_t21_non_git_root_is_fail_closed(tmp_path):
    """SPEC Task 2.1 邊界⑥：非 git 樹 ⇒ fail-closed，不得靜默退回只掃 target。"""
    reg = {"k": {"target": "docs/a.md", "rows": [["010", "ZZID"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = tmp_path / "nogit"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "a.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n010\tZZID\n<!-- END GENERATED: k -->\n",
        encoding="utf-8")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "非 git 樹卻通過 ⇒ 靜默退回，fail-open"
    assert "非 git 工作樹" in r.stderr


def test_t21_symlink_in_scope_is_fail_closed(tmp_path):
    """SPEC Task 2.1：symlink／gitlink 一律 fail-closed（不遞迴、不略過）。"""
    reg = {"k": {"target": "docs/a.md", "rows": [["010", "ZZID"]]}}
    sdir = _sandbox(tmp_path, reg)
    root = _mkroot(tmp_path)
    (root / "docs" / "a.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n010\tZZID\n<!-- END GENERATED: k -->\n",
        encoding="utf-8")
    (root / "outside.md").write_text("x\n", encoding="utf-8")
    (root / "docs" / "link.md").symlink_to(root / "outside.md")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "symlink 未 fail-closed"
    assert "symlink" in r.stderr


# ==========================================================================
# 待辦清單 WL-01 — schema 由平面列擴為具名欄／表格投影
#
# 出處：`x-consult-r12` J-1（codex＋composer 同判）——`.rows[]|@tsv` 只有平面列，
#   承載不了「現行／已廢」兩欄之判準表 ⇒ 票 B-25 之「判準資料化」無從施工。
#   本節即該限制解除後的守衛：**加法**（未宣告 columns/render 者行為不變）＋
#   **新不變式**（宣告 columns 後掉欄／多欄當場 fail-closed）。
# ==========================================================================

_WL01_ROWS = [["020", "b", "後"], ["010", "a", "前"]]


def _shape_reg(**extra):
    """單 key 註冊表；extra 覆寫該 key 之欄位（columns／render／rows）。"""
    key = {"target": "t.md", "rows": _WL01_ROWS}
    key.update(extra)
    return {"k": key}


def _emit(tmp_path: Path, registry: dict, sub: str = "s"):
    """只跑生成（無宿主檔需求）；回傳 CompletedProcess。"""
    sdir = _sandbox(tmp_path / sub, registry)
    return _run([str(sdir / GEN.name)])


# --- 加法性：未宣告者逐位元組不變 ------------------------------------------

def test_wl01_absent_columns_and_render_keeps_flat_tsv_bytes(tmp_path):
    """WL-01 是加法：不宣告 columns／render ⇒ 輸出與擴充前逐位元組相同。

    這條是**相容性錨**：一旦有人把 table 設成預設，或在 tsv 路徑上多印表頭，本測試轉紅。
    """
    r = _emit(tmp_path, _shape_reg())
    assert r.returncode == 0, r.stderr
    assert r.stdout == (
        "<!-- BEGIN GENERATED: k -->\n"
        "010\ta\t前\n"
        "020\tb\t後\n"
        "<!-- END GENERATED: k -->\n"
    ), r.stdout


def test_wl01_columns_alone_does_not_change_output(tmp_path):
    """只宣告 columns（render 仍為預設 tsv）⇒ 輸出不變，只是多了列長不變式。"""
    a = _emit(tmp_path, _shape_reg(), sub="a")
    b = _emit(tmp_path, _shape_reg(columns=["序", "名", "註"]), sub="b")
    assert a.returncode == 0 and b.returncode == 0, (a.stderr, b.stderr)
    assert a.stdout == b.stdout, "宣告 columns 不得改變 tsv 投影"


# --- table 投影的形狀與排序 -------------------------------------------------

def test_wl01_table_render_emits_header_separator_then_sorted_rows(tmp_path):
    r = _emit(tmp_path, _shape_reg(columns=["序", "名", "註"], render="table"))
    assert r.returncode == 0, r.stderr
    assert r.stdout == (
        "<!-- BEGIN GENERATED: k -->\n"
        "| 序 | 名 | 註 |\n"
        "|---|---|---|\n"
        "| 010 | a | 前 |\n"
        "| 020 | b | 後 |\n"
        "<!-- END GENERATED: k -->\n"
    ), r.stdout


def test_wl01_render_does_not_change_row_order(tmp_path):
    """兩種 render 共用同一排序點 ⇒ 換 render 不換順序。

    反面才有鑑別力：若 table 路徑自己排一次（例如排渲染後的 `| …` 字串），
    分隔符不同會在「某格是另一格之前綴」時給出不同次序 ⇒ 本測試轉紅。
    """
    # 鑑別力來源：`a` 是 `a b` 的前綴，其後的分隔字元不同——
    #   TSV 比 `\t`(0x09) vs ` `(0x20) ⇒ `a` 在前；渲染後比 `|`(0x7C) vs `b`(0x62) ⇒ `a b` 在前。
    #   兩者次序相反 ⇒ 若 table 分支自己再排一次，本測試轉紅。
    rows = [["010", "a", "x"], ["010", "a b", "y"]]
    tsv = _emit(tmp_path, {"k": {"target": "t.md", "rows": rows}}, sub="tsv")
    tab = _emit(tmp_path, {"k": {"target": "t.md", "columns": ["1", "2", "3"],
                                 "render": "table", "rows": rows}}, sub="tab")
    assert tsv.returncode == 0 and tab.returncode == 0, (tsv.stderr, tab.stderr)
    order_tsv = [ln.split("\t") for ln in tsv.stdout.splitlines()[1:-1]]
    order_tab = [[c.strip() for c in ln.strip("|").split("|")]
                 for ln in tab.stdout.splitlines()[3:-1]]
    assert order_tsv == order_tab, f"tsv={order_tsv} table={order_tab}"


def test_wl01_table_write_then_check_round_trip(tmp_path):
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text(
        "前言\n<!-- BEGIN GENERATED: k -->\n舊\n<!-- END GENERATED: k -->\n後記\n",
        encoding="utf-8",
    )
    sdir = _sandbox(tmp_path, {"k": {"target": "docs/t.md", "columns": ["a", "b", "c"],
                                     "render": "table", "rows": _WL01_ROWS}})
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    assert _run([str(sdir / GEN.name), "--check"], env_extra=env).returncode == 0
    body = (root / "docs" / "t.md").read_text(encoding="utf-8")
    assert body.startswith("前言\n") and body.endswith("後記\n")
    assert "| a | b | c |\n|---|---|---|\n" in body


# --- fail-closed 面 ---------------------------------------------------------

@pytest.mark.parametrize("columns", [
    [],                      # 空陣列
    ["a", "a"],              # 重複欄名
    ["a", ""],               # 空字串欄名
    ["a", 1],                # 非字串
    ["a", "b|c"],            # 含 | （table 會被切碎）
    ["a", "b\tc"],           # 含 tab（破壞 @tsv 逐列語義）
    "abc",                   # 非陣列
])
def test_wl01_illegal_columns_is_fail_closed(tmp_path, columns):
    r = _emit(tmp_path, _shape_reg(columns=columns))
    assert r.returncode != 0, f"columns={columns!r} 應 fail-closed\n{r.stdout}"


def test_wl01_row_length_mismatch_is_fail_closed(tmp_path):
    """宣告三欄卻有一列只有兩格 ⇒ 拒。擴充前此列會靜默產出參差 TSV。"""
    reg = _shape_reg(columns=["a", "b", "c"], rows=[["010", "x", "y"], ["020", "z"]])
    r = _emit(tmp_path, reg)
    assert r.returncode != 0, r.stdout
    assert "欄數" in r.stderr, r.stderr


@pytest.mark.parametrize("render", ["markdown", "TSV", "", 1, None])
def test_wl01_unknown_render_is_fail_closed(tmp_path, render):
    r = _emit(tmp_path, _shape_reg(columns=["a", "b", "c"], render=render))
    assert r.returncode != 0, f"render={render!r} 應 fail-closed\n{r.stdout}"


def test_wl01_table_render_without_columns_is_fail_closed(tmp_path):
    """無表頭的表格不是表格 ⇒ 不得靜默退回 tsv。"""
    r = _emit(tmp_path, _shape_reg(render="table"))
    assert r.returncode != 0, r.stdout
    assert "columns" in r.stderr, r.stderr


@pytest.mark.parametrize("bad", ["含\t分隔", "含\n換行"])
def test_wl01_cell_with_tab_or_newline_is_fail_closed(tmp_path, bad):
    """兩種 render 皆拒：tab／換行會讓「一列一行」的語義崩掉。"""
    for extra, sub in ((dict(), "tsv"),
                       (dict(columns=["a", "b", "c"], render="table"), "tab")):
        reg = _shape_reg(rows=[["010", bad, "z"]], **extra)
        r = _emit(tmp_path, reg, sub=f"{sub}-{len(bad)}")
        assert r.returncode != 0, f"{sub}: {bad!r} 應 fail-closed\n{r.stdout}"


def test_wl01_table_cell_with_pipe_is_fail_closed(tmp_path):
    reg = _shape_reg(columns=["a", "b", "c"], render="table",
                     rows=[["010", "含|管線", "z"]])
    r = _emit(tmp_path, reg)
    assert r.returncode != 0, r.stdout
    assert "|" in r.stderr


def test_wl01_pipe_in_cell_is_allowed_under_tsv_render(tmp_path):
    """🔴 只在 table 模式禁 `|`。tsv 模式不受影響——否則就是趁機加嚴既有 key。"""
    r = _emit(tmp_path, _shape_reg(rows=[["010", "含|管線", "z"]]))
    assert r.returncode == 0, r.stderr


# --- mutation：證明新檢查承重（拿掉即壞資料被放行）--------------------------

def test_wl01_mutation_removing_length_check_lets_ragged_rows_through(tmp_path):
    """引信：把列長比對改成恆真 ⇒ 參差列被放行 ⇒ 證明該檢查真的在擋。"""
    reg = _shape_reg(columns=["a", "b", "c"], rows=[["010", "x", "y"], ["020", "z"]])
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, "length == $n", "length >= 0")
    assert _run([str(good / GEN.name)]).returncode != 0
    assert _run([str(bad / GEN.name)]).returncode == 0, "這條 mutation 是空心的"


def test_wl01_mutation_removing_shape_call_in_check_lets_bad_render_through(tmp_path):
    """引信：`--check` 路徑若不呼叫形狀驗證，非法 render 會一路走到字串比對。"""
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n", encoding="utf-8")
    reg = {"k": {"target": "docs/t.md", "render": "markdown", "rows": [["010", "a"]]}}
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, '_fk_validate_shape "${_fkc_k}" || { _fkc_rc=1; continue; }', ":")
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    g = _run([str(good / GEN.name), "--check"], env_extra=env)
    b = _run([str(bad / GEN.name), "--check"], env_extra=env)
    assert g.returncode != 0 and "render" in g.stderr, g.stderr
    assert "render" not in b.stderr, "拿掉呼叫後仍報 render ⇒ 這條 mutation 是空心的"


def test_wl01_sort_anchor_stays_unique_in_generator():
    """🔴 T-2.1-M1 的**前提**：`_mutate` 用 `replace(..., 1)` 只改第一處。

    出生事故（2026-08-10）已因錨點撞到 `_fk_targets` 的去重排序而誤打一次。
    WL-01 新增 table 分支時若各自寫一行排序，錨點會再度變成兩處 ⇒ 兩條 mutation
    打不到生成排序而**空心通過**。修法＝排序集中在 `_fk_rows_tsv`；本測試釘住之。
    """
    src = GEN.read_text(encoding="utf-8")
    n = src.count(_ROWS_SORT_ANCHOR)
    assert n == 1, (
        f"排序錨點 {_ROWS_SORT_ANCHOR!r} 在生產檔出現 {n} 次（須恰 1）——"
        "T-2.1-M1a／M1b 會打到第一處而非生成排序，成為空心 mutation"
    )


def test_wl01_handwritten_status_detector_still_works_under_table_render(tmp_path):
    """render 改變不得削弱手寫狀態偵測：識別碼仍由 rows 第 2 欄導出（讀 JSON，非讀投影）。"""
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n", encoding="utf-8")
    (root / "docs" / "prose.md").write_text("ZZ-01 已落地\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, {
        "_schema": {
            "status_enum": ["已落地"],
            "status_keys": ["k"],
            "status_scope": ["docs/"],
            "status_scope_grandfathered": ["docs/__none__.md"],
        },
        "k": {"target": "docs/t.md", "columns": ["序", "項", "狀"],
              "render": "table", "rows": [["010", "ZZ-01", "已落地"]]},
    })
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode != 0, "table render 下偵測器失效 ⇒ 手寫狀態可繞過"
    assert "HANDWRITTEN STATUS" in r.stderr and "prose.md" in r.stderr, r.stderr
