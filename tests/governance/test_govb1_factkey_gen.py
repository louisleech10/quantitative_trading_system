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
import re
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
    frozen, added, criteria, mechanism, enforcement = [], [], [], [], []
    for line in AMENDMENT.read_text(encoding="utf-8").splitlines():
        if line.startswith("FACTKEY-FROZEN: "):
            frozen.append(line[len("FACTKEY-FROZEN: "):].strip())
        elif line.startswith("FACTKEY-ADDED: "):
            added.append(line[len("FACTKEY-ADDED: "):].strip())
        elif line.startswith("FACTKEY-CRITERIA: "):
            criteria.append(line[len("FACTKEY-CRITERIA: "):].strip())
        elif line.startswith("FACTKEY-MECHANISM: "):
            mechanism.append(line[len("FACTKEY-MECHANISM: "):].strip())
        elif line.startswith("FACTKEY-ENFORCEMENT: "):
            enforcement.append(line[len("FACTKEY-ENFORCEMENT: "):].strip())
    assert frozen, "延伸檔缺 FACTKEY-FROZEN 宣告 → fail-closed"
    assert added, "延伸檔缺 FACTKEY-ADDED 宣告 → fail-closed"
    assert criteria, "延伸檔缺 FACTKEY-CRITERIA 宣告 → fail-closed（WL-02 起）"
    assert mechanism, "延伸檔缺 FACTKEY-MECHANISM 宣告 → fail-closed（WL-03 起）"
    assert enforcement, "延伸檔缺 FACTKEY-ENFORCEMENT 宣告 → fail-closed（產出端覆蓋規則起）"
    lists = (("FROZEN", frozen), ("ADDED", added), ("CRITERIA", criteria),
             ("MECHANISM", mechanism), ("ENFORCEMENT", enforcement))
    for name, lst in lists:
        assert len(lst) == len(set(lst)), f"FACTKEY-{name} 含重複項: {lst}"
    sets = [set(lst) for _, lst in lists]
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            assert not (sets[i] & sets[j]), (
                f"宣告清單 {lists[i][0]} 與 {lists[j][0]} 不得交集: {sorted(sets[i] & sets[j])}"
            )
    return tuple(sets)


def test_registry_key_set_equals_amendment_declaration():
    """票 B-25 站 2.5 Task 1.4（原 TODO 實作要點 1 之延伸；偏離登記見 docs/GOV_B25_SCOPE_AMENDMENT.md）。

    🔴 五條**集合相等**（禁 issubset/>=/in）：
      ① registry 全集 == FROZEN ∪ ADDED ∪ CRITERIA ∪ MECHANISM
      ② ADDED == _schema.status_keys（r3 CODEX-R3-P1-04：破解自我循環——
         單靠①時延伸檔漏列一個 key，三方仍互相一致而無人轉紅）
      ②b CRITERIA == _schema.criteria_keys（WL-02 起；理由同②）
      ②c MECHANISM == _schema.mechanism_keys（WL-03 起；理由同②）
      ③ 凍結期單一 key 仍須在 FROZEN 內
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    fact_keys = {k for k in data if k != "_schema"}
    frozen, added, criteria, mechanism, enforcement = _amendment_keys()

    assert fact_keys == frozen | added | criteria | mechanism | enforcement, (
        f"registry key 集合與延伸檔宣告不符：registry={sorted(fact_keys)} "
        f"vs 宣告={sorted(frozen | added | criteria | mechanism | enforcement)}"
    )
    assert KEY in frozen, f"凍結期單一 key {KEY} 未列於 FACTKEY-FROZEN"

    status_keys = set(data["_schema"]["status_keys"])
    assert added == status_keys, (
        "🔴 延伸檔 ADDED 與 _schema.status_keys 不相等 ⇒ 可能漏交或多交狀態 key："
        f"ADDED={sorted(added)} vs status_keys={sorted(status_keys)}"
    )
    criteria_keys = set(data["_schema"].get("criteria_keys", []))
    assert criteria == criteria_keys, (
        "🔴 延伸檔 CRITERIA 與 _schema.criteria_keys 不相等 ⇒ 判準 key 漏交或多交："
        f"CRITERIA={sorted(criteria)} vs criteria_keys={sorted(criteria_keys)}"
    )
    mechanism_keys = set(data["_schema"].get("mechanism_keys", []))
    assert mechanism == mechanism_keys, (
        "🔴 延伸檔 MECHANISM 與 _schema.mechanism_keys 不相等 ⇒ 機制 key 漏交或多交："
        f"MECHANISM={sorted(mechanism)} vs mechanism_keys={sorted(mechanism_keys)}"
    )
    enforcement_keys = set(data["_schema"].get("enforcement_keys", []))
    assert enforcement == enforcement_keys, (
        "🔴 延伸檔 ENFORCEMENT 與 _schema.enforcement_keys 不相等 ⇒ 產出端覆蓋 key 漏交或多交："
        f"ENFORCEMENT={sorted(enforcement)} vs enforcement_keys={sorted(enforcement_keys)}"
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
# 🔴 S0.6：governance-ticket-closure 已刪除（第二套可獨立編輯的票狀態源）。
#    票狀態之唯一來源改為 governance-ticket-sot；宣稱限制併入其「狀態依據」欄。
_SOT_KEY = "governance-ticket-sot"

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

def test_e3_ticket_union_is_covered_by_sot():
    """S0.6 後之 §E3：union（HANDOFF 活缺口 ∪ backlog scope 缺口子節）須**被票 SoT 涵蓋**。

    🔴 語意由「恰等於」改為「子集」，因為承載對象換了：
      原 governance-ticket-closure 只收錄「有宣稱限制的票」，故與 union 相等；
      governance-ticket-sot 是**全集**（61 張），union 只會是它的子集。
      要求相等會恆紅，且會誘使把 SoT 縮成部分集合——與「唯一全集」的目的相反。
    涵蓋方向仍是有效保證：union 中任一票若不在 SoT，即代表 SoT 漏收，須 fail。
    B3R 為批次非票（見 governance-batch-status），不在 SoT，故排除。
    """
    op1 = _section(REPO / "HANDOFF.md", r"^## 🔴 未修的活缺口", r"^## ")
    op2 = _section(REPO / "handoffs" / "20260801-GOV-AMEND-BACKLOG.md",
                   r"^### 🔴 2026-08-10 scope 缺口", r"^### ")
    union = {t for t in (set(_tok(op1)) | set(_tok(op2))) if t != "B3R"}
    rows = {r[1] for r in _rows(_SOT_KEY)}
    missing = sorted(union - rows)
    assert not missing, f"E3 union 有票不在票 SoT（漏收）：{missing}（第三方可重跑）"


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
    for key, col in ((_BATCH_KEY, 2), (_SOT_KEY, 2)):
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
        # 🔴 新增（票 SoT 上線）：該檔已標作廢、改由 docs/GOV_TICKET_SOT.md 承載票狀態。
        #    其內 8 處歷史狀態符號刻意不逐行清除（歷史紀錄，且「修正只考慮以後」為使用者定死）。
        #    本測試在該檔加入豁免時**實際擋下過主委一次**——這正是它存在的目的。
        "白話說明/治理待辦總覽.md",
    }
    got = set(json.loads(REG.read_text(encoding="utf-8"))
              ["_schema"]["status_scope_grandfathered"])
    assert got == expected, (
        f"豁免清單與本表不相等：多={sorted(got - expected)} 少={sorted(expected - got)}。"
        "新增豁免須同時修訂本表並經審查——這正是「不得靜默加入豁免」的機械強制點。"
    )


def test_s11_enforcement_ticket_allowlist_is_locked_by_set_equality():
    """S1.1：非票標的白名單以集合相等鎖死 ⇒ 不得靜默把新值加進 enforcement 的對應票欄。

    🔴 白名單存在的唯一正當性＝使用者定死之鐵律原文明文點名 G-7 與 pytest
       （「除非像 G-7 和 pytest 等可以說明為何不該放在產出端」）。
       任何第三個值都不是使用者點名的，必須經審查才能進來——本表即該審查的機械載體。
    """
    expected = {"G-7", "測試套件"}
    got = set(json.loads(REG.read_text(encoding="utf-8"))
              ["_schema"]["enforcement_ticket_allowlist"])
    assert got == expected, (
        f"非票標的白名單與本表不相等：多={sorted(got - expected)} 少={sorted(expected - got)}。"
        "白名單是「合法的非票標的」之封閉集合；靜默新增等於為幽靈票開後門。"
    )


def test_s11_ghost_ticket_is_rejected(tmp_path):
    """S1.1 反例（可證偽）：對應票填票全集外之值 ⇒ rc≠0 且訊息具名該值。

    🔴 斷言訊息而非只看 rc——本 epic 已兩次因「紅在別的原因」而誤把空心檢查當成通過。
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    ekey = data["_schema"]["enforcement_keys"][0]
    tcol = data["_schema"]["enforcement_column_roles"]["ticket"]
    ti = data[ekey]["columns"].index(tcol)
    data[ekey]["rows"][0][ti] = "B-99999"      # 票全集內不存在，且不在 allowlist
    sdir = _sandbox(tmp_path, data)            # data 已含 _schema ⇒ 不注入最小 schema

    r = _run([str(sdir / GEN.name), "--check"],
             env_extra={"GOVB1_FACTKEY_ROOT": str(REPO)})
    assert r.returncode != 0, f"幽靈票未被擋（rc=0）：{r.stdout}{r.stderr}"
    assert "B-99999" in (r.stdout + r.stderr), (
        f"rc≠0 但訊息未具名該幽靈票值 ⇒ 可能紅在別的原因：{r.stdout}{r.stderr}"
    )


def test_s22_pending_coverage_warns_without_failing(tmp_path):
    """S2.2：『部分完成』且未登記覆蓋之票，須**提前預警**且**不判紅**。

    🔴 兩個斷言缺一不可：
      · 只驗「有警告」⇒ 無法排除它同時把樹判紅（那會逼人不敢記錄真實狀態）
      · 只驗「不判紅」⇒ 無法排除警告根本沒印（等於沒有預警）
    🔴 本測試**自行構造**待預警的票，不依賴現樹狀態——初版直接對現樹斷言，
       在 S4.3 把所有已交付票補登記後即轉紅（預警正確地不再出現）。
       依賴環境狀態的測試不是可證偽的測試。
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    tk = data["_schema"]["enforcement_ticket_roles"]
    cols = data[tk["key"]]["columns"]
    idi, sti = cols.index(tk["id"]), cols.index(tk["status"])
    row = list(data[tk["key"]]["rows"][0])
    row[idi], row[sti] = "B-88888", "部分完成"          # 未登記於 enforcement
    data[tk["key"]]["rows"].append(row)
    sdir = _sandbox(tmp_path, data)

    r = _run([str(sdir / GEN.name), "--check"],
             env_extra={"GOVB1_FACTKEY_ROOT": str(REPO)})
    assert "S2.2 預警" in r.stderr, f"未見預警訊息 ⇒ 提前告知未生效：{r.stderr}"
    assert "B-88888" in r.stderr, f"預警未具名該票 ⇒ 訊息無法據以行動：{r.stderr}"
    assert "與強制側不一致" not in r.stderr, "預警不應牽動判定型檢查"


def test_s12_missing_settings_with_dir_present_is_fail_closed(tmp_path):
    """S1.2：hook 設定之承載目錄存在、設定檔缺失 ⇒ fail-closed（非「大聲印出後放行」）。

    🔴 原行為：設定檔不存在即略過全部掛載點對證 ⇒ **刪掉它就能跳過**（codex：
       「大聲印出不是阻擋」）。修法以**目錄是否存在**區分兩種情況，判準封閉可判定。
    本測試與 test_s12_missing_settings_dir_is_skipped 成對，證明修法精準而非一律判紅。
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    sdir = _sandbox(tmp_path, data)
    (sdir.parent / ".claude").mkdir(parents=True, exist_ok=True)   # 承載目錄在、設定檔不在

    r = _run([str(sdir / GEN.name), "--check"],
             env_extra={"GOVB1_FACTKEY_ROOT": str(REPO)})
    assert r.returncode != 0, f"設定檔缺失卻放行 ⇒ fail-open：{r.stdout}{r.stderr}"
    assert "設定檔缺失" in (r.stdout + r.stderr), (
        f"rc≠0 但未具名設定檔缺失 ⇒ 可能紅在別的原因：{r.stdout}{r.stderr}"
    )


def test_s12_missing_settings_dir_is_skipped(tmp_path):
    """S1.2 對照：承載目錄本身不存在 ⇒ 仍略過（真的非主控端環境，fixture 不得整批誤紅）。"""
    data = json.loads(REG.read_text(encoding="utf-8"))
    sdir = _sandbox(tmp_path, data)                                 # 不建 .claude/

    r = _run([str(sdir / GEN.name), "--check"],
             env_extra={"GOVB1_FACTKEY_ROOT": str(REPO)})
    assert "非主控端環境" in (r.stdout + r.stderr), (
        f"承載目錄不存在時未走略過路徑 ⇒ 最小 fixture 會整批誤紅：{r.stdout}{r.stderr}"
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
    ["a", "b\rc"],           # 🔴 CODEX-R1-P1-01：CR 會把表頭拆行
    ["a", "b\nc"],           # LF 同上
    ["a", "b\x01c"],         # 其餘控制字元（封閉集合，非逐個列舉）
    ["a", "b\x7fc"],         # DEL
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


def test_wl01_r1_p1_01_cr_in_column_name_cannot_produce_silent_malformed_table(tmp_path):
    """🔴 CODEX-R1-P1-01 閉合回歸（以其原始反例逐字重現）。

    病：初版禁字元是**列舉黑名單**（`|` / tab / LF），漏了 CR。
        表頭那兩行**不經 @tsv**（cells 才經），故 raw CR 直接進產出、把表頭拆成兩行；
        `--check` 比的是字串，宿主同樣壞掉即兩邊相符 ⇒ **rc=0 靜默放行**。
    修法：改為封閉集合（`|` ∪ `[[:cntrl:]]`），表頭與儲存格共用同一集合。

    本測試同時釘住兩件事，缺一即無法證明缺口真的關上：
      ① emit 必須 rc≠0（不得只是「輸出變好看」）
      ② 產出中不得出現 CR（防有人改成「靜默剝除」——那會讓資料與宿主不再等價）
    """
    reg = _shape_reg(columns=["a\rb", "c", "d"], render="table")
    r = _emit(tmp_path, reg)
    assert r.returncode != 0, f"CR 欄名未 fail-closed（原始缺口未關）\n{r.stdout!r}"
    assert "\r" not in r.stdout, "產出仍含 CR ⇒ 改成了靜默剝除而非拒絕"
    assert "控制字元" in r.stderr, r.stderr


@pytest.mark.parametrize("bad", ["\r", "\x01", "\x0b", "\x7f"])
def test_wl01_control_char_in_cell_is_fail_closed(tmp_path, bad):
    """儲存格側同樣走封閉集合。

    `@tsv` 只轉義 `\\t \\n \\r \\\\` —— 其餘控制字元原樣輸出，故不能只靠它。
    """
    reg = _shape_reg(columns=["a", "b", "c"], render="table",
                     rows=[["010", f"x{bad}y", "z"]])
    r = _emit(tmp_path, reg, sub=f"c{ord(bad)}")
    assert r.returncode != 0, f"儲存格控制字元 {bad!r} 未 fail-closed\n{r.stdout!r}"


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


# ==========================================================================
# 待辦清單 WL-02 — 判準資料化（票 B-25）
#
# 設計依據：handoffs/reconcile/20260813-govwl02-x-consult-r1/synth.md（三家 consult）。
# 主委原提案三處落法被推翻並改寫，詳見該檔；本節只守最終落法。
#
# 🔴 本節**不**測「語意互斥」——三家一致認定：不同條件字串描述同一物理事件時鍵不相等，
#    機械上偵測不到。那是具名殘留（docs/GOV_CRITERIA_REGISTRY.md 殘留 1），不是本機制的能力。
#    若有人日後為此加測試，請先讀該殘留，別把「測不到」寫成「測過了」。
# ==========================================================================

_CRIT_ROLES = {"id": "判準ID", "scope": "適用範圍", "condition": "條件",
               "expect": "期望rc", "status": "狀態", "oracle": "對應測試"}
_CRIT_COLS = ["判準ID", "適用範圍", "條件", "期望rc", "狀態", "對應測試"]
_CRIT_ENUM = ["現行", "已廢"]


def _crit_reg(rows, *, roles=None, enum=None, cols=None, target="docs/c.md"):
    """判準註冊表；預設一列合法資料。刻意讓 _schema 完整以免被前置檢查攔在前面。"""
    return {
        "_schema": {
            "status_enum": ["✅"],
            "status_keys": ["other"],
            "status_scope": ["docs/"],
            "status_scope_grandfathered": ["docs/__none__.md"],
            "criteria_keys": ["crit"],
            "criteria_status_enum": _CRIT_ENUM if enum is None else enum,
            "criteria_column_roles": _CRIT_ROLES if roles is None else roles,
            "criteria_live_status": "現行",
        },
        "other": {"target": "docs/o.md", "rows": [["010", "ZZ-01", "x"]]},
        "crit": {"target": target, "columns": _CRIT_COLS if cols is None else cols,
                 "render": "table", "rows": rows},
    }


_CRIT_OK = [["C-1", "s1", "cond-a", "0", "現行", "test_a"],
            ["C-2", "s1", "cond-b", "1", "現行", "test_b"]]


def _crit_root(tmp_path, *, body="", cname="c.md"):
    root = _mkroot(tmp_path)
    (root / "docs" / cname).write_text(
        "前言\n<!-- BEGIN GENERATED: crit -->\n<!-- END GENERATED: crit -->\n" + body,
        encoding="utf-8")
    (root / "docs" / "o.md").write_text(
        "<!-- BEGIN GENERATED: other -->\n<!-- END GENERATED: other -->\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    return root


def _crit_run(tmp_path, registry, *, body="", sub="s"):
    root = _crit_root(tmp_path / sub, body=body)
    sdir = _sandbox(tmp_path / sub, registry)
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    # 🔴 `--write` 的 rc 不得丟棄：本 helper 的多數用例餵的就是壞註冊表，`--write` 會先擋下，
    #    此時若仍往下跑 `--check`，看到的是「區塊沒寫成」的 DRIFT，真正的錯因被掩蓋
    #    ——2026-08-13 一次偶發紅即因此無從診斷。故 write 擋下時直接回傳它。
    #    （不可改成 assert rc==0：那會讓「本來就該被 write 擋下」的四條測試轉紅。）
    w = _run([str(sdir / GEN.name), "--write"], env_extra=env)
    if w.returncode != 0 and "DRIFT" not in w.stderr:
        return w, sdir, root
    return _run([str(sdir / GEN.name), "--check"], env_extra=env), sdir, root


def test_wl02_clean_criteria_table_is_rc_zero(tmp_path):
    r, _, _ = _crit_run(tmp_path, _crit_reg(_CRIT_OK))
    assert r.returncode == 0, r.stderr


def test_wl02_conflicting_criteria_is_fail_closed(tmp_path):
    """WL-02 字面要求：同適用範圍同條件、狀態為現行，期望相異 ⇒ 拒。"""
    rows = _CRIT_OK + [["C-3", "s1", "cond-a", "1", "現行", "test_c"]]
    r, _, _ = _crit_run(tmp_path, _crit_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "互斥判準" in r.stderr and "cond-a" in r.stderr, r.stderr


def test_wl02_superseded_row_does_not_count_as_conflict(tmp_path):
    """已廢列刻意不參與衝突判定 —— 否則「現行／已廢」兩欄表本身就永遠紅。

    這正是 x-consult-r12 J-1 當初指出、WL-01 才解除的那種表。
    """
    rows = _CRIT_OK + [["C-3", "s1", "cond-a", "1", "已廢", "見 C-1"]]
    r, _, _ = _crit_run(tmp_path, _crit_reg(rows))
    assert r.returncode == 0, r.stderr


def test_wl02_unknown_criteria_status_is_fail_closed(tmp_path):
    """🔴 CODEX-R1-P1-03：未宣告封閉列舉時，未知狀態值會被當普通字串默默接受。"""
    rows = [["C-1", "s1", "cond-a", "0", "大概吧", "test_a"]]
    r, _, _ = _crit_run(tmp_path, _crit_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "criteria_status_enum" in r.stderr, r.stderr


def test_wl02_missing_role_column_is_fail_closed(tmp_path):
    """角色欄由名稱解析，不寫死索引；欄名對不上即拒（而非默默取錯欄）。"""
    cols = ["判準ID", "適用範圍", "條件", "期望rc", "狀態", "測試"]  # oracle 欄改名
    rows = [["C-1", "s1", "cond-a", "0", "現行", "test_a"]]
    r, _, _ = _crit_run(tmp_path, _crit_reg(rows, cols=cols))
    assert r.returncode != 0, r.stdout
    assert "缺角色欄" in r.stderr, r.stderr


@pytest.mark.parametrize("claim", [
    "驗收：rc=0",
    "驗收：rc = 1",
    "此路徑 rc≠0",
    "此路徑 rc != 0",
    "邊界②：具名略過、rc 不變",
    "期望 returncode == 1",
    # 🔴 以下為 r2 三家各自掃描本庫**實測導出**之補漏（主委原六種被證偽）：
    "Exit code: 0",                 # GROK-R2-P1-01：本庫 ≥58 行
    "exit code 1",
    "期望退出碼 1",                  # COMPOSER-R2-P1-01／GROK-R2-P1-01
    "結束碼 0",
    "非零退出",
    "returncode != 0",              # 單等號／不等號皆須攔（原只攔 ==）
    "returncode = 0",
    "→ exit 1",                     # COMPOSER-R2-P1-01
    "rc: 0",
    "期望 rc 為 0",
])
def test_wl02_rc_claim_outside_block_is_fail_closed(tmp_path, claim):
    """🔴 COMPOSER-R1-P1-01／GROK-R1-P1-02：只釘 `rc=` 會被同義寫法繞過。

    封閉白名單的每一種形態都必須被抓到；其中 `returncode ==` 是 docs/ 內**已存在**的用法。
    """
    r, _, _ = _crit_run(tmp_path, _crit_reg(_CRIT_OK), body=claim + "\n",
                        sub=f"c{abs(hash(claim)) % 9973}")
    assert r.returncode != 0, f"{claim!r} 未被攔截\n{r.stdout}"
    assert "生成區塊外陳述期望結束狀態" in r.stderr, r.stderr


@pytest.mark.parametrize("claim", [
    "最終結束狀態與第一份一致",
    "由通過變為不通過",
])
def test_wl02_relational_claims_are_named_residual_not_caught(tmp_path, claim):
    """🔴 具名殘留釘樁（`CODEX-R2-P1-01` 之關係型例）。

    白名單刻意**不**涵蓋關係型／轉換型陳述——那需要理解語意，納入即退化成無限黑名單。
    本測試斷言的是「現況不攔」，**不是「這樣才對」**：若哪天有人把它攔住了，
    這裡會轉紅，提醒他回頭更新 docs/GOV_CRITERIA_REGISTRY.md 殘留 6，
    而不是留著一句過期的「我們沒防這個」。
    """
    r, _, _ = _crit_run(tmp_path, _crit_reg(_CRIT_OK), body=claim + "\n",
                        sub=f"rel{abs(hash(claim)) % 9973}")
    assert r.returncode == 0, (
        f"{claim!r} 已被攔截 ⇒ 殘留 6 的涵蓋宣稱已過期，請同步更新 "
        f"docs/GOV_CRITERIA_REGISTRY.md 與 _FK_RC_CLAIM_FORMS\n{r.stderr}"
    )


def test_wl02_claim_form_list_is_frozen_named_set():
    """白名單之涵蓋面須有具名清單，且與正則同批維護。

    只有正則沒有清單時，「涵蓋哪些」只存在於一串難讀的字元類裡，
    文件要引用就只能再抄一份 —— 那就是本註冊表要治的病。
    """
    src = GEN.read_text(encoding="utf-8")
    m = re.search(r"^_FK_RC_CLAIM_FORMS='([^']*)'$", src, re.M)
    assert m, "生產檔缺 _FK_RC_CLAIM_FORMS 具名清單"
    forms = m.group(1).split()
    assert forms == sorted(set(forms), key=forms.index), "具名清單不得有重複項"
    assert set(forms) == {
        "rc-op", "rc-unchanged", "returncode-op", "exit-code",
        "exit-n", "exitcode-zh", "endcode-zh", "nonzero-zh",
    }, (
        f"白名單涵蓋面已變動（現為 {forms}）——請同時更新 "
        "docs/GOV_CRITERIA_REGISTRY.md 殘留 6 與本測試，不得只改其一"
    )


def test_wl02_criteria_schema_fields_are_one_unit(tmp_path):
    """🔴 CODEX-R2-P1-02：原版單獨刪 criteria_keys 即靜默停用三道檢查。

    四欄任一存在 ⇒ 四欄全需存在；整組缺席才算「本註冊表無判準」。
    """
    for drop in ("criteria_keys", "criteria_status_enum",
                 "criteria_column_roles", "criteria_live_status"):
        reg = _crit_reg(_CRIT_OK)
        del reg["_schema"][drop]
        r = _emit(tmp_path, reg, sub=f"d{drop}")
        assert r.returncode != 0, f"單獨刪 {drop} 未 fail-closed\n{r.stdout}"


def test_wl02_empty_criteria_keys_is_fail_closed(tmp_path):
    reg = _crit_reg(_CRIT_OK)
    reg["_schema"]["criteria_keys"] = []
    r = _emit(tmp_path, reg)
    assert r.returncode != 0, r.stdout
    assert "靜默停用" in r.stderr, r.stderr


def test_wl02_live_status_is_named_not_positional(tmp_path):
    """🔴 GROK-R2-P2-01：原版取 criteria_status_enum[0] 當「現行」＝位置契約。

    重排 enum 不得改變語義：現行列的互斥仍須被抓到。
    """
    rows = _CRIT_OK + [["C-3", "s1", "cond-a", "1", "現行", "test_c"]]
    reg = _crit_reg(rows, enum=["已廢", "現行"])       # 首元刻意不是現行
    r, _, _ = _crit_run(tmp_path, reg)
    assert r.returncode != 0, "enum 重排後現行互斥被漏掉 ⇒ 語義掛在位置上"
    assert "互斥判準" in r.stderr, r.stderr


def test_wl02_live_status_outside_enum_is_fail_closed(tmp_path):
    reg = _crit_reg(_CRIT_OK)
    reg["_schema"]["criteria_live_status"] = "在職"
    r = _emit(tmp_path, reg)
    assert r.returncode != 0, r.stdout


def test_wl02_rc_claim_inside_own_block_is_allowed(tmp_path):
    """判準表本身就在寫期望值 —— 區塊內不得被自己咬。"""
    rows = [["C-1", "s1", "cond-a", "0", "現行", "test_a"]]
    r, _, _ = _crit_run(tmp_path, _crit_reg(rows))
    assert r.returncode == 0, r.stderr


def test_wl02_rc_claim_inside_other_key_block_is_allowed(tmp_path):
    """🔴 COMPOSER-R1-P1-03：多 key 宿主須豁免**該檔全部**合法區塊，非只判準區塊。

    只豁免判準區塊時，同檔並存的其他事實表會被誤擋。
    """
    reg = _crit_reg(_CRIT_OK)
    reg["other"]["target"] = "docs/c.md"          # 同檔兩個 key
    reg["other"]["rows"] = [["010", "ZZ-01", "rc=0"]]
    root = _mkroot(tmp_path)
    (root / "docs" / "c.md").write_text(
        "前言\n<!-- BEGIN GENERATED: crit -->\n<!-- END GENERATED: crit -->\n"
        "<!-- BEGIN GENERATED: other -->\n<!-- END GENERATED: other -->\n",
        encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, reg)
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode == 0, f"同檔其他 key 之區塊內容被誤擋\n{r.stderr}"


def test_wl02_non_target_file_is_not_scanned_named_residual(tmp_path):
    """🔴 CODEX-R1-P1-02 之**具名殘留釘樁**：membership 靠登記，不靠有沒有區塊。

    未登記檔即使貼一組看起來像判準表的生成標記、並在區塊外寫期望值，**也不會被掃**。
    本測試斷言的是「現況如此」，不是「這樣才對」——它存在的目的是：
    若哪天有人以為這條已經封住，這裡會提醒他沒有。
    殘留全文見 docs/GOV_CRITERIA_REGISTRY.md 殘留 2。
    """
    root = _crit_root(tmp_path)
    (root / "docs" / "unregistered.md").write_text(
        "<!-- BEGIN GENERATED: crit -->\n<!-- END GENERATED: crit -->\n驗收 rc=0\n",
        encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, _crit_reg(_CRIT_OK))
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    _run([str(sdir / GEN.name), "--write"], env_extra=env)
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert "生成區塊外陳述期望結束狀態" not in r.stderr, (
        "未登記檔已被納入 rc 掃描 ⇒ 殘留 2 已關閉，請更新 "
        "docs/GOV_CRITERIA_REGISTRY.md 與本測試，不要留著過期的殘留宣稱"
    )


def test_wl02_mutation_removing_conflict_check_lets_contradiction_through(tmp_path):
    rows = _CRIT_OK + [["C-3", "s1", "cond-a", "1", "現行", "test_c"]]
    reg = _crit_reg(rows)
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, "_fk_validate_criteria || _fkc_rc=1", ":")
    root = _crit_root(tmp_path / "r")
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    _run([str(good / GEN.name), "--write"], env_extra=env)
    g = _run([str(good / GEN.name), "--check"], env_extra=env)
    b = _run([str(bad / GEN.name), "--check"], env_extra=env)
    assert g.returncode != 0 and "互斥判準" in g.stderr, g.stderr
    assert "互斥判準" not in b.stderr, "拿掉呼叫仍報互斥 ⇒ 這條 mutation 是空心的"


def test_wl02_mutation_removing_rc_scan_lets_outside_claim_through(tmp_path):
    reg = _crit_reg(_CRIT_OK)
    good = _sandbox(tmp_path / "good", reg)
    bad = _sandbox(tmp_path / "bad", reg)
    _mutate(bad, "_fk_reject_rc_claims_outside_blocks || _fkc_rc=1", ":")
    root = _crit_root(tmp_path / "r", body="驗收：rc=0\n")
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    _run([str(good / GEN.name), "--write"], env_extra=env)
    g = _run([str(good / GEN.name), "--check"], env_extra=env)
    b = _run([str(bad / GEN.name), "--check"], env_extra=env)
    assert g.returncode != 0, g.stderr
    assert b.returncode == 0, f"拿掉 rc 掃描後仍紅 ⇒ 這條 mutation 是空心的\n{b.stderr}"


def test_wl02_live_criteria_oracle_tests_exist():
    """🔴 CODEX-R1-P1-03 之修法：判準表不得退化成無人對照的散文目錄。

    每個「現行」判準的『對應測試』欄，必須真的是 tests/ 底下存在的測試函式。
    這條把「表」與「真正承重的東西」綁在一起 —— 表自己不承重，測試才承重。
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    ckeys = data["_schema"]["criteria_keys"]
    roles = data["_schema"]["criteria_column_roles"]
    # 🔴 讀具名欄，不取 enum[0]：後者是位置契約，GROK-R2-P2-01 已於生產碼改掉，
    #    本測試當時漏改 ⇒ 重排 enum 即靜默改變「現行」的定義（WL-03 施工時補正）。
    live = data["_schema"]["criteria_live_status"]
    src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((REPO / "tests" / "governance").glob("*.py"))
    )
    missing = []
    for k in ckeys:
        cols = data[k]["columns"]
        si, oi = cols.index(roles["status"]), cols.index(roles["oracle"])
        idi = cols.index(roles["id"])
        for row in data[k]["rows"]:
            if row[si] != live:
                continue
            if f"def {row[oi]}(" not in src:
                missing.append(f"{row[idi]} → {row[oi]}")
    assert not missing, (
        "判準表之『對應測試』不存在於 tests/governance/ ⇒ 該判準無人承重：\n  "
        + "\n  ".join(missing)
    )


# ==========================================================================
# WL-03（票 B-25 機制證據登記）
#
# 設計出處：handoffs/reconcile/20260813-govwl03-x-consult-r1/synth.md（三家 consult）。
# 主委原提案「掃改法段抽反引號 span」被三家各自實測否決（誤擋率 80–93%）⇒ 改為
# 「專用登記表 ＋ 顯式 opt-in 宿主 ＋ receipt/assumed 只對資料列驗證」，禁掃散文。
#
# 🔴 本區塊的測試同時釘住**三條刻意保留的殘留**（它們是設計決定，不是漏做）：
#   · test_wl03_non_optin_host_is_not_scanned_named_residual        （殘留 2）
#   · test_wl03_heading_style_gaifa_is_named_residual               （殘留 5）
#   · test_wl03_receipt_existence_is_not_content_verification       （殘留 4）
#   若哪天封住了其中之一，該測試會轉紅 —— 屆時請回頭更新
#   docs/GOV_MECHANISM_REGISTRY.md 的殘留宣稱，不要只改測試。

_MECH_ROLES = {"id": "機制ID", "token": "平台機制", "scope": "適用範圍",
               "evidence": "證據", "finding": "實跑結論", "status": "狀態"}
_MECH_COLS = ["機制ID", "平台機制", "適用範圍", "證據", "實跑結論", "狀態"]
_MECH_TOKENS = ["setsid", "ulimit", "timeout", "flock", "nohup", "taskset"]
_MECH_OK = [["M-1", "timeout", "s1", "receipt:docs/r.md", "可用", "現行"],
            ["M-2", "flock", "s2", "assumed:尚未採用", "未實跑", "現行"]]


def _mech_reg(rows, *, roles=None, cols=None, tokens=None, scope=None,
              enum=None, live="現行", drop=()):
    schema = {
        "status_enum": ["✅"],
        "status_keys": ["other"],
        "status_scope": ["docs/"],
        "status_scope_grandfathered": ["docs/__none__.md"],
        "mechanism_keys": ["mech"],
        "mechanism_status_enum": ["現行", "已廢"] if enum is None else enum,
        "mechanism_live_status": live,
        "mechanism_column_roles": _MECH_ROLES if roles is None else roles,
        "mechanism_scope": ["docs/m.md", "docs/spec.md"] if scope is None else scope,
        "mechanism_tokens": _MECH_TOKENS if tokens is None else tokens,
    }
    for f in drop:
        schema.pop(f, None)
    return {
        "_schema": schema,
        "other": {"target": "docs/o.md", "rows": [["010", "ZZ-01", "x"]]},
        "mech": {"target": "docs/m.md", "columns": _MECH_COLS if cols is None else cols,
                 "render": "table", "rows": rows},
    }


def _mech_root(tmp_path, *, spec_body="", receipt=True):
    """建宿主根。

    🔴 receipt 檔放在 **root 內**（＝正在驗的那棵樹）〔CODEX-R1-P1-03〕。
    初版放在 sandbox 父層（生成器所在 repo），使 root 缺 receipt 時仍被 repo 同名檔
    遮蔽而 rc=0 —— codex 以 decoy 實構重現。
    """
    root = _mkroot(tmp_path)
    (root / "docs" / "m.md").write_text(
        "前言\n<!-- BEGIN GENERATED: mech -->\n<!-- END GENERATED: mech -->\n",
        encoding="utf-8")
    (root / "docs" / "o.md").write_text(
        "<!-- BEGIN GENERATED: other -->\n<!-- END GENERATED: other -->\n", encoding="utf-8")
    (root / "docs" / "spec.md").write_text("# spec\n" + spec_body, encoding="utf-8")
    (root / "docs" / "outside.md").write_text("# 不在 opt-in 清單內\n", encoding="utf-8")
    if receipt:
        (root / "docs" / "r.md").write_text("實跑記錄\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    return root


def _mech_run(tmp_path, registry, *, spec_body="", receipt=True, mode="--check",
              mutate=None):
    root = _mech_root(tmp_path, spec_body=spec_body, receipt=receipt)
    sdir = _sandbox(tmp_path, registry)
    if mutate is not None:
        _mutate(sdir, *mutate)
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    if mode == "--check":
        # 前置 write 的 rc 刻意**不** assert：本 helper 的多數用例就是要讓 write 也擋下
        # （schema 壞、receipt 缺檔等），此處只在 write 綠時才有意義往下比 DRIFT。
        w = _run([str(sdir / GEN.name), "--write"], env_extra=env)
        if w.returncode != 0 and "DRIFT" not in w.stderr:
            # write 已擋下 ⇒ 直接回傳它，避免下游 DRIFT 掩蓋真正錯因
            return w, sdir, root
    args = [str(sdir / GEN.name)] + ([mode] if mode else [])
    return _run(args, env_extra=env), sdir, root


# `- 改法` 子樹寫法：機制在**續行**上（GROK-R1-P1-03 指出同行-only 會漏掉它）
_GAIFA_CONTINUATION = (
    "\n**Task 9.9** 收尾\n\n"
    "- 改法：把每一行丟進獨立 process group，\n"
    "  收尾以 `nohup` 脫離終端後終止整群。\n"
    "- 驗證：見下節\n"
)


def test_wl03_clean_mechanism_table_is_rc_zero(tmp_path):
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK))
    assert r.returncode == 0, r.stderr


def test_wl03_illegal_evidence_form_is_fail_closed(tmp_path):
    """判準 C-013：證據欄前綴為封閉集合 {receipt, assumed}，其餘一律拒。

    這是本機制的核心 —— 沒有這條，作者可以寫任何看起來像證據的字串。
    """
    rows = [["M-1", "timeout", "s1", "probably:我覺得可以", "可用", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "證據" in r.stderr and "前綴" in r.stderr, r.stderr


def test_wl03_receipt_pointing_at_missing_file_is_fail_closed(tmp_path):
    """判準 C-014：宣稱 receipt 但檔不存在 ⇒ 拒。

    🔴 出生事故的形狀就是這個：文件寫了機制、讀起來像已驗證，實際上無物可查。
    """
    rows = [["M-1", "timeout", "s1", "receipt:docs/NO_SUCH.md", "可用", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "receipt 指向不存在之檔" in r.stderr, r.stderr


def test_wl03_receipt_existence_is_not_content_verification(tmp_path):
    """🔴 具名殘留 4（刻意）：receipt 只驗檔案存在，不驗內容真的記載那次實跑。

    指向一個存在但完全無關的檔會通過。若哪天這條被封住（改成驗內容），
    本測試會轉紅 —— 屆時請回頭更新 docs/GOV_MECHANISM_REGISTRY.md 殘留 4 的宣稱。
    """
    rows = [["M-1", "timeout", "s1", "receipt:docs/r.md", "可用", "現行"]]
    r, _, root = _mech_run(tmp_path, _mech_reg(rows))
    # docs/r.md 的內容是「實跑記錄」四個字，與 timeout 毫無關係
    assert r.returncode == 0, (
        "receipt 內容驗證若已上線，殘留 4 的宣稱就過期了 —— 請更新登記表而非只改測試\n"
        + r.stderr
    )


def test_wl03_assumed_evidence_is_allowed(tmp_path):
    """assumed 是**顯式未驗標記**，允許通過 —— 本機制治的是「沒說」，不是「沒跑」。"""
    rows = [["M-1", "setsid", "s1", "assumed:本機不確定是否存在，尚未實跑", "未驗", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode == 0, r.stderr


def test_wl03_empty_evidence_body_is_fail_closed(tmp_path):
    """`assumed:` 後面空白 ⇒ 拒。否則「顯式標記」退化成一個字面前綴。"""
    rows = [["M-1", "timeout", "s1", "assumed:", "未驗", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "缺冒號後之內容" in r.stderr, r.stderr


def test_wl03_token_outside_closed_table_is_fail_closed(tmp_path):
    """登記了但拼錯 ⇒ 拒。

    否則作者登記 `tiemout`、掃描仍抓 `timeout` 而紅，作者卻以為自己已經登記過了。
    """
    rows = [["M-1", "tiemout", "s1", "receipt:docs/r.md", "可用", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "mechanism_tokens" in r.stderr, r.stderr


def test_wl03_duplicate_mechanism_id_is_fail_closed(tmp_path):
    rows = [["M-1", "timeout", "s1", "receipt:docs/r.md", "可用", "現行"],
            ["M-1", "flock", "s2", "assumed:x", "未驗", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows))
    assert r.returncode != 0, r.stdout
    assert "重複機制ID" in r.stderr, r.stderr


def test_wl03_unregistered_mechanism_in_gaifa_subtree_is_fail_closed(tmp_path):
    """判準 C-015：opt-in 宿主的 `- 改法` 子樹用了未登記機制 ⇒ 拒。

    🔴 機制在**續行**上 —— GROK-R1-P1-03 實測指出「只掃同行含改法」會漏掉它，
    出生事故的 `ulimit -H -u` 正是寫在續行。
    """
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=_GAIFA_CONTINUATION)
    assert r.returncode != 0, r.stdout
    assert "nohup" in r.stderr and "未登記為現行" in r.stderr, r.stderr


def test_wl03_registering_the_mechanism_turns_it_green(tmp_path):
    """同一份文字，登記之後就通過 —— 證明擋的是「未登記」而不是「出現該字串」。"""
    rows = _MECH_OK + [["M-3", "nohup", "s3", "assumed:待實跑", "未驗", "現行"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows), spec_body=_GAIFA_CONTINUATION)
    assert r.returncode == 0, r.stderr


def test_wl03_superseded_mechanism_does_not_count_as_registered(tmp_path):
    """已廢的登記列不算數 —— 否則廢掉一條就等於永久豁免。"""
    rows = _MECH_OK + [["M-3", "nohup", "s3", "assumed:待實跑", "未驗", "已廢"]]
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows), spec_body=_GAIFA_CONTINUATION)
    assert r.returncode != 0, r.stdout
    assert "nohup" in r.stderr, r.stderr


def test_wl03_non_optin_host_is_not_scanned_named_residual(tmp_path):
    """判準 C-016 ＋ 🔴 具名殘留 2（刻意）：不在 mechanism_scope 的檔完全不掃。

    三家否決了「凡含 FACT-RECEIPT」（回掃 53 檔＝溯及既往）與「凡新建 GOV*」
    （未封閉 glob）⇒ membership 只靠登記。若哪天改成掃全庫，本測試會轉紅，
    屆時請回頭更新 docs/GOV_MECHANISM_REGISTRY.md 殘留 2 的宣稱。
    """
    root = _mech_root(tmp_path)
    (root / "docs" / "outside.md").write_text(
        "# 不在 opt-in 清單內\n" + _GAIFA_CONTINUATION, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, _mech_reg(_MECH_OK))
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    _run([str(sdir / GEN.name), "--write"], env_extra=env)
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode == 0, (
        "非 opt-in 宿主若已被掃，殘留 2 的宣稱就過期了 —— 請更新登記表而非只改測試\n"
        + r.stderr
    )


def test_wl03_heading_style_gaifa_is_named_residual(tmp_path):
    """🔴 具名殘留 5（刻意）：子樹起點釘死 `- 改法`，標題式寫法不涵蓋。

    本庫 `^#+.*改法` 標題僅 3 個（掃標題＝零訊號），而全檔搜「改法」二字
    經三家實測誤擋率 80–93% ⇒ 兩端都不可取，故取中間的 bullet 形態。
    """
    body = "\n## 改法\n\n收尾以 `nohup` 脫離終端。\n"
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode == 0, (
        "標題式改法若已被涵蓋，殘留 5 的宣稱就過期了 —— 請更新登記表而非只改測試\n"
        + r.stderr
    )


def test_wl03_subtree_ends_at_next_bullet(tmp_path):
    """子樹邊界：`- 驗證` 之後的機制不屬於改法子樹，不得溢出誤擋。"""
    body = ("\n- 改法：改用 Edit 工具寫檔。\n"
            "- 驗證：手動確認 `nohup` 這個字在驗證段裡不該被當成改法機制。\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode == 0, r.stderr


# ---- r1 三家實構之子樹旁路（初版全部漏掃；修法＝改用單一縮排判準）----

def test_wl03_nested_bullet_in_gaifa_subtree_is_scanned(tmp_path):
    """🔴 三家全員實構〔CODEX-R1-P1-01／GROK-R1-P1-01／COMPOSER-R1-P1-01〕。

    本庫慣用「`- 改法：` 底下掛縮排子彈」寫步驟（GOVB25:143、DISPATCH:288 即此形），
    初版把**任何**縮排層級的 `- ` 當終點 ⇒ 起點的下一行就截斷，整段改法漏掃。
    """
    body = ("\n- 改法：\n"
            "  - 步驟一：收尾以 `nohup` 脫離終端。\n"
            "- 驗證：見下節\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode != 0, f"巢狀子彈上的未登記機制漏掃\n{r.stdout}"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_blank_line_does_not_end_gaifa_subtree(tmp_path):
    """🔴 GROK-R1-P1-02 實構：多段改法之第二段整段漏掃。

    初版把空行當終點；改法寫成「一段、空行、再一段」是常見排版。
    """
    body = ("\n- 改法：把每一行丟進獨立 process group，\n"
            "\n"
            "  收尾以 `setsid` 建立新 session 後終止整群。\n"
            "- 驗證：見下節\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode != 0, f"空行後續行上的未登記機制漏掃\n{r.stdout}"
    assert "setsid" in r.stderr, r.stderr


@pytest.mark.parametrize("start", ["- 🔴 **改法**：", "- **改法**：", "- 改法："])
def test_wl03_decorated_gaifa_start_is_scanned(tmp_path, start):
    """🔴 GROK-R1-P2-01 實構：opt-in 宿主內已存在 `- 🔴 **改法` 與 `- **改法`。

    起點正則若只認樸素寫法，那兩種形態整段零覆蓋（DISPATCH:213、:264 即此形）。
    """
    body = f"\n{start}收尾以 `nohup` 脫離終端。\n- 驗證：見下節\n"
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode != 0, f"裝飾起點 {start!r} 之改法子樹漏掃\n{r.stdout}"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_bold_paragraph_start_ends_subtree_named_residual(tmp_path):
    """🔴 具名殘留 7（刻意）：縮排 0 的粗體段首終止子樹，且該行本身不掃。

    〔COMPOSER-R1-P1-02 判 BLOCKING，主委裁定為殘留〕理由：`**Task**` 在縮排 0
    是新段落的慣例標記；若改成「先掃再終止」，`- 驗證：` 那類行也會被納入改法子樹
    而製造新的誤擋。若哪天改了判定，本測試會轉紅 —— 屆時請更新登記表殘留 7。
    """
    body = ("\n- 改法：改用零執行路徑。\n"
            "**Task 9.9** 另一件事：用 `flock` 互斥。\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode == 0, (
        "粗體段首若已納入掃描，殘留 7 的宣稱就過期了 —— 請更新登記表而非只改測試\n"
        + r.stderr
    )


def test_wl03_indented_bold_stays_inside_subtree(tmp_path):
    """與上一條的對照：**縮排**的粗體仍屬改法正文，不得被當成段落終點。

    🔴 探針必須用**未登記**的 token（`nohup`）—— 初版誤用 `flock`，
    而 `flock` 在 `_MECH_OK` 已登記為現行，測試因此恆綠（自造的空心格）。
    """
    body = ("\n- 改法：改用零執行路徑，\n"
            "  **關鍵**：以 `nohup` 做背景化。\n"
            "- 驗證：見下節\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode != 0, f"縮排粗體上的未登記機制漏掃\n{r.stdout}"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_nested_gaifa_start_does_not_overwrite_boundary(tmp_path):
    """🔴 CODEX-R2-P1-01（r2 唯一 BLOCKING，三家中僅一家構造出來）。

    `- 改法：` 底下再寫一個縮排的 `- 改法：`（內層步驟），內層起點會把 boundary
    抬到縮排 2 ⇒ 其後同級的續行（縮排 2）當場被判終止而漏掃。
    另兩家判「無第四旁路」，係未測此形態——採碼證不採家數。
    """
    body = ("\n- 改法：\n"
            "  - 改法：內層步驟。\n"
            "  - 外層續行使用 `nohup` 脫離終端。\n"
            "- 驗證：見下節\n")
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK), spec_body=body)
    assert r.returncode != 0, f"巢狀 `- 改法` 覆寫 boundary ⇒ 後續同級續行漏掃\n{r.stdout}"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_jq_failure_is_fail_closed_not_empty_registry(tmp_path):
    """🔴 r2 三家皆觀察到之偶發紅，根因：`jq` 的 rc 被 process substitution 吞掉。

    `_fk_raw_keys` 失敗時原本被靜默當成「註冊表沒有任何 fact-key」，後果兩個方向都有：
      · criteria／mechanism 驗證 ⇒ 所有 key 判「未註冊」＝**假紅**（三家看到的就是這個）
      · schema_sets／handwritten_status 的「無 fact-key ⇒ rc=0」語意 ⇒ **假綠**
    本測試釘住：jq 失敗必須報出**真正的病**，而不是誤導到「key 未註冊」。
    """
    root = _mech_root(tmp_path)
    sdir = _sandbox(tmp_path, _mech_reg(_MECH_OK))
    _mutate(sdir, """_fk_raw_keys() { LC_ALL=C jq -r 'keys[]' "${REG}"; }""",
            "_fk_raw_keys() { return 1; }")
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, "jq 失敗被當成空註冊表而放行 ⇒ 假綠"
    assert "讀取 fact-key 清單失敗" in r.stderr, (
        f"jq 失敗未報出真正的病 ⇒ 診斷會被導向錯誤方向\n{r.stderr}"
    )
    assert "未註冊 key" not in r.stderr, (
        f"jq 失敗仍偽裝成「key 未註冊」⇒ 就是本輪偶發紅的誤導形狀\n{r.stderr}"
    )


def test_wl03_receipt_root_is_the_scanned_tree_not_generator_repo(tmp_path):
    """🔴 CODEX-R1-P1-03 實構：receipt 必須對**正在驗的那棵樹**判定。

    初版讓 receipt 相對生成器所在 repo ⇒ 被驗的 root 缺 receipt 時，
    仍被生成器自身 repo 的同名檔遮蔽而 rc=0（decoy 遮蔽）。
    """
    rows = [["M-1", "timeout", "s1", "receipt:docs/r.md", "可用", "現行"]]
    # receipt=False ⇒ 被驗的 root 內沒有 docs/r.md；真 repo 內也沒有同路徑檔可遮蔽，
    # 但本測試的重點是「查的是 root」——故同時斷言錯誤訊息指向缺檔。
    r, _, _ = _mech_run(tmp_path, _mech_reg(rows), receipt=False)
    assert r.returncode != 0, f"被驗的 root 缺 receipt 卻通過 ⇒ 查錯了 root\n{r.stdout}"
    assert "receipt 指向不存在之檔" in r.stderr, r.stderr


def test_wl03_symlink_receipt_is_fail_closed(tmp_path):
    """🔴 CODEX-R1-P2-04 實構：`-f` 會跟隨連結 ⇒ receipt 可指向 repo 之外。

    與 `_fk_reject_handwritten_status` 對 symlink 的處置同一紀律。
    """
    rows = [["M-1", "timeout", "s1", "receipt:docs/link.md", "可用", "現行"]]
    root = _mech_root(tmp_path, receipt=True)
    outside = tmp_path / "outside-receipt.md"
    outside.write_text("repo 外的東西\n", encoding="utf-8")
    (root / "docs" / "link.md").symlink_to(outside)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, _mech_reg(rows))
    r = _run([str(sdir / GEN.name), "--check"], env_extra={"GOVB1_FACTKEY_ROOT": str(root)})
    assert r.returncode != 0, f"symlink receipt 通過 ⇒ 證據可指向 repo 外\n{r.stdout}"
    assert "symlink" in r.stderr, r.stderr


def test_wl03_subtree_scan_also_runs_on_write(tmp_path):
    """🔴 COMPOSER-R1-P2-01：`--write` 本來就讀寫宿主檔，漏掛會讓單跑 --write 暫時綠。"""
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK),
                        spec_body=_GAIFA_CONTINUATION, mode="--write")
    assert r.returncode != 0, f"--write 未跑子樹掃描\n{r.stdout}"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_subtree_scan_not_on_emit_named_residual(tmp_path):
    """🔴 具名殘留 8（刻意）：emit 是純 stdout 投影、不讀宿主檔，故不跑子樹掃描。

    掛上去等於憑空要求一棵樹。承重在 `--check`（`gov_check` 走這條）與 `--write`。
    若哪天 emit 也掃了，本測試會轉紅 —— 屆時請更新登記表殘留 8。
    """
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK),
                        spec_body=_GAIFA_CONTINUATION, mode="")
    assert r.returncode == 0, (
        "emit 若已跑子樹掃描，殘留 8 的宣稱就過期了 —— 請更新登記表而非只改測試\n"
        + r.stderr
    )


def test_wl03_mechanism_schema_fields_are_one_unit(tmp_path):
    """🔴 WL-02 CODEX-R2-P1-02 同型：單獨刪一欄不得靜默停用全部檢查。

    整組缺席＝宣稱無機制登記（合法，由延伸檔集合相等承接）；
    部分缺席＝設定錯誤，必須 fail-closed。
    """
    for field in ["mechanism_keys", "mechanism_tokens", "mechanism_scope",
                  "mechanism_live_status", "mechanism_status_enum",
                  "mechanism_column_roles"]:
        reg = _mech_reg(_MECH_OK, drop=(field,))
        r, _, _ = _mech_run(tmp_path / field.replace("_", ""), reg)
        assert r.returncode != 0, f"單獨刪 {field} 後仍 rc=0 ⇒ 檢查被靜默停用\n{r.stdout}"
        assert field in r.stderr, r.stderr


def test_wl03_checks_run_on_all_three_paths(tmp_path):
    """🔴「檢查只掛在其中一條路徑上」是本 epic 一天內出現四次的形態。

    emit／--check／--write 三條路徑都必須擋同一個壞資料列。
    """
    rows = [["M-1", "timeout", "s1", "receipt:docs/NO_SUCH.md", "可用", "現行"]]
    for i, mode in enumerate(["", "--check", "--write"]):
        r, _, _ = _mech_run(tmp_path / f"p{i}", _mech_reg(rows), mode=mode)
        assert r.returncode != 0, (
            f"路徑 {mode or 'emit'} 未擋下 receipt 缺檔 ⇒ 該路徑漏掛檢查\n{r.stdout}"
        )


def test_wl03_missing_optin_host_is_fail_closed(tmp_path):
    """🔴 缺檔不得靜默略過 —— 「缺檔＝略過」正是 G-7 上一輪被 codex 抓到的 fail-open。"""
    reg = _mech_reg(_MECH_OK, scope=["docs/m.md", "docs/spec.md", "docs/gone.md"])
    r, _, _ = _mech_run(tmp_path, reg)
    assert r.returncode != 0, r.stdout
    assert "宿主不存在" in r.stderr and "gone.md" in r.stderr, r.stderr


@pytest.mark.parametrize("bad,why", [
    ("docs/*.md", "不得含 wildcard"),
    ("docs/", "須為 exact path"),
    ("/abs/x.md", "絕對路徑或含 .."),
    ("docs/../x.md", "絕對路徑或含 .."),
])
def test_wl03_scope_must_be_exact_paths(tmp_path, bad, why):
    """opt-in 必須逐檔顯式：wildcard／目錄前綴／絕對路徑／`..` 一律拒。

    這是與 WL-02 status_scope 的**刻意差異** —— 那邊允許目錄前綴，
    這邊不允許，因為「顯式 opt-in」正是三家用來取代未封閉 glob 的東西。

    🔴 斷言**精確錯因**，不只斷言 `mechanism_scope` 出現〔CODEX-R1-P1-02〕：
    這些 bad path 對應的檔都不存在，缺檔本身就會報 `mechanism_scope 所列宿主不存在`
    ⇒ 移除語法守衛後測試仍綠。codex 以 mutation 實測三項斷言全 PASS。
    """
    reg = _mech_reg(_MECH_OK, scope=["docs/m.md", "docs/spec.md", bad])
    r, _, _ = _mech_run(tmp_path, reg)
    assert r.returncode != 0, r.stdout
    assert why in r.stderr, (
        f"未報出精確錯因 {why!r} ⇒ 可能是缺檔判定在頂替語法守衛（假綠）\n{r.stderr}"
    )


def test_wl03_mutation_removing_scope_syntax_guard_turns_green(tmp_path):
    """反面實證：拿掉 scope 語法守衛後，wildcard 就不再以語法錯因被擋。

    〔CODEX-R1-P1-02 之修法配套〕—— 證明上面那組斷言真的釘在守衛上。
    """
    reg = _mech_reg(_MECH_OK, scope=["docs/m.md", "docs/spec.md", "docs/*.md"])
    good, _, _ = _mech_run(tmp_path / "g", reg)
    # 🔴 錨點必須唯一：`*'*'*|*'?'*|*'['*)` 在 status_scope 的守衛裡也有一份，
    #   `_mutate` 只換第一處 ⇒ 會打到那邊而空心（初版即如此）。故連同專屬變數一起錨定。
    bad, _, _ = _mech_run(tmp_path / "b", reg, mutate=(
        '    case "${_fkvm_sc}" in\n      *\'*\'*|*\'?\'*|*\'[\'*)',
        '    case "${_fkvm_sc}" in\n      __never_match__)'))
    assert "不得含 wildcard" in good.stderr, good.stderr
    assert "不得含 wildcard" not in bad.stderr, (
        f"拿掉 wildcard 守衛後仍報同一錯因 ⇒ 這條斷言是空心的\n{bad.stderr}"
    )


def test_wl03_role_columns_resolved_by_name_not_index(tmp_path):
    """角色欄由名稱解析；欄名對不上即拒，而非默默取錯欄。"""
    cols = ["機制ID", "平台機制", "適用範圍", "憑證", "實跑結論", "狀態"]  # evidence 欄改名
    r, _, _ = _mech_run(tmp_path, _mech_reg(_MECH_OK, cols=cols))
    assert r.returncode != 0, r.stdout
    assert "缺角色欄" in r.stderr, r.stderr


def test_wl03_live_status_is_named_not_positional(tmp_path):
    """🔴 GROK-R2-P2-01 同型：「現行」以具名欄宣告，不以 enum 位置承載語義。

    把 enum 重排後行為不得改變 —— 若改變，代表某處又退回讀 enum[0]。
    """
    reg = _mech_reg(_MECH_OK + [["M-3", "nohup", "s3", "assumed:x", "未驗", "已廢"]],
                    enum=["已廢", "現行"], live="現行")
    r, _, _ = _mech_run(tmp_path, reg, spec_body=_GAIFA_CONTINUATION)
    assert r.returncode != 0, "enum 重排後『已廢』被當成現行 ⇒ 又退回位置契約"
    assert "nohup" in r.stderr, r.stderr


def test_wl03_mutation_removing_subtree_scan_lets_unregistered_through(tmp_path):
    """反面實證：拿掉子樹掃描後，未登記機制就通過 ⇒ 證明上面那條不是空心格。"""
    reg = _mech_reg(_MECH_OK)
    good, _, _ = _mech_run(tmp_path / "g", reg, spec_body=_GAIFA_CONTINUATION)
    # 🔴 錨在**函式定義**上，不錨在呼叫點：r1 修補後子樹掃描有兩個呼叫點
    #   （`--check` 與 `--write`），只 mutate 一處會讓 `--write` 仍紅而測不到東西。
    bad, _, _ = _mech_run(tmp_path / "b", reg, spec_body=_GAIFA_CONTINUATION, mutate=(
        "_fk_reject_unregistered_mechanisms() {\n  _fk_mechanism_schema_present || return 0",
        "_fk_reject_unregistered_mechanisms() {\n  return 0"))
    assert good.returncode != 0, good.stderr
    assert bad.returncode == 0, (
        f"拿掉子樹掃描後仍紅 ⇒ 這條 mutation 是空心的\n{bad.stderr}"
    )


def test_wl03_mutation_removing_receipt_check_lets_missing_file_through(tmp_path):
    """反面實證：拿掉 receipt 存在性判定後，缺檔就通過。"""
    rows = [["M-1", "timeout", "s1", "receipt:docs/NO_SUCH.md", "可用", "現行"]]
    reg = _mech_reg(rows)
    good, _, _ = _mech_run(tmp_path / "g", reg)
    # 🔴 `[ -f X ] || { 報錯 }` 的反面是 `true ||`，不是 `false ||`
    #    —— 後者反而**必定**進入報錯分支（本測試初版即打反，由紅燈抓到）
    bad, _, _ = _mech_run(tmp_path / "b", reg,
                          mutate=('[ -f "$(_fk_root)/${_fkvm_val}" ] || {', "true || {"))
    assert good.returncode != 0, good.stderr
    assert bad.returncode == 0, (
        f"拿掉 receipt 存在性判定後仍紅 ⇒ 這條 mutation 是空心的\n{bad.stderr}"
    )


def test_wl03_token_matching_is_literal_table_not_path_probe():
    """🔴 GROK-R1-P1-03 之修法釘子：token 比對必須是**字面表**，不得改成 PATH 探測。

    本機 `setsid` 不在 PATH ⇒ 以 `command -v`／`which` 做候選會**漏掉出生事故本身**。
    這是被實測直接證偽過的 assumed，不得回退。
    """
    src = GEN.read_text(encoding="utf-8")
    body = src.split("WL-03（票 B-25 機制證據登記）", 1)[1]
    for probe in ["command -v", "which ", "type -P"]:
        assert probe not in body, (
            f"WL-03 區段出現 PATH 探測 {probe!r} ⇒ setsid 不在 PATH，這會漏掉出生事故本身"
        )
    data = json.loads(REG.read_text(encoding="utf-8"))
    toks = data["_schema"]["mechanism_tokens"]
    assert "setsid" in toks and "ulimit" in toks, (
        "封閉表須含出生事故的兩個機制，否則這條規則對它自己的起因無感"
    )


def test_wl03_live_mechanism_oracle_tests_exist():
    """機制表所引的判準（C-013–C-016）之對應測試須真的存在。

    與 WL-02 同一紀律：表不承重，測試才承重。
    """
    data = json.loads(REG.read_text(encoding="utf-8"))
    ckeys = data["_schema"]["criteria_keys"]
    roles = data["_schema"]["criteria_column_roles"]
    live = data["_schema"]["criteria_live_status"]
    src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((REPO / "tests" / "governance").glob("*.py"))
    )
    missing = []
    for k in ckeys:
        cols = data[k]["columns"]
        si, oi = cols.index(roles["status"]), cols.index(roles["oracle"])
        idi = cols.index(roles["id"])
        for row in data[k]["rows"]:
            if row[si] != live or not row[idi].startswith("C-01"):
                continue
            if f"def {row[oi]}(" not in src:
                missing.append(f"{row[idi]} → {row[oi]}")
    assert not missing, "WL-03 判準之對應測試不存在：\n  " + "\n  ".join(missing)


def test_wl03_production_registry_scope_hosts_all_exist():
    """生產註冊表的 opt-in 宿主必須都存在（否則 --check 會在真樹上恆紅）。"""
    data = json.loads(REG.read_text(encoding="utf-8"))
    missing = [p for p in data["_schema"]["mechanism_scope"] if not (REPO / p).is_file()]
    assert not missing, f"mechanism_scope 所列宿主不存在: {missing}"


def test_wl03_production_receipts_all_exist():
    """生產登記表的每個 receipt: 都要指向真檔 —— 這條在真樹上跑，不靠 fixture。"""
    data = json.loads(REG.read_text(encoding="utf-8"))
    roles = data["_schema"]["mechanism_column_roles"]
    bad = []
    for k in data["_schema"]["mechanism_keys"]:
        ei = data[k]["columns"].index(roles["evidence"])
        for row in data[k]["rows"]:
            ev = row[ei]
            if ev.startswith("receipt:") and not (REPO / ev[len("receipt:"):]).is_file():
                bad.append(ev)
    assert not bad, f"receipt 指向不存在之檔: {bad}"


def test_wl01_handwritten_status_detector_still_works_under_table_render(tmp_path):
    """render 改變不得削弱手寫狀態偵測：識別碼仍由 rows 第 2 欄導出（讀 JSON，非讀投影）。"""
    root = _mkroot(tmp_path)
    (root / "docs" / "t.md").write_text(
        "<!-- BEGIN GENERATED: k -->\n<!-- END GENERATED: k -->\n", encoding="utf-8")
    # 🔴 狀態值刻意用「待審」而非「已落地」：S2.1 起「已落地」屬**完成語意集合**，
    #   會連帶要求 registry 具備完整 enforcement schema，使本測試被無關的規則牽動。
    #   本測試的標的是「render 改變不得削弱手寫狀態偵測」，與完成語意綁定無關 ⇒ 換值不損意圖。
    (root / "docs" / "prose.md").write_text("ZZ-01 待審\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    sdir = _sandbox(tmp_path, {
        "_schema": {
            "status_enum": ["待審"],
            "status_keys": ["k"],
            "status_scope": ["docs/"],
            "status_scope_grandfathered": ["docs/__none__.md"],
        },
        "k": {"target": "docs/t.md", "columns": ["序", "項", "狀"],
              "render": "table", "rows": [["010", "ZZ-01", "待審"]]},
    })
    env = {"GOVB1_FACTKEY_ROOT": str(root)}
    assert _run([str(sdir / GEN.name), "--write"], env_extra=env).returncode == 0
    r = _run([str(sdir / GEN.name), "--check"], env_extra=env)
    assert r.returncode != 0, "table render 下偵測器失效 ⇒ 手寫狀態可繞過"
    assert "HANDWRITTEN STATUS" in r.stderr and "prose.md" in r.stderr, r.stderr
