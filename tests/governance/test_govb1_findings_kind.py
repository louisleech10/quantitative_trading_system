"""GOVB1 Task 4.1（`票 B-38`）— findings-kind 機械分類判準。

受測物：``scripts/findings_kind_classify.sh``（本批新建，**無 caller**）。

判準必須是**可證偽**的：每個實作要素都附一條 mutation，證明拿掉它會有斷言轉紅。
特別是兩條「凍結 TODO 偽碼照抄會壞掉」的地方（欄位名、jq `//` 對 false 的處理），
各有專屬回歸——那兩個 bug 都是**靜默**的（不報錯、只是全部判成 unknown）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLASSIFY = REPO_ROOT / "scripts" / "findings_kind_classify.sh"
LIFECYCLE = REPO_ROOT / "scripts" / "govflow_lifecycle.json"


def _run(
    args: list[str], *, lifecycle: Path | None = None, script: Path = CLASSIFY
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if lifecycle is not None:
        env["FINDINGS_KIND_LIFECYCLE"] = str(lifecycle)
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )


def _brief(path: Path, kind: str | None, *, body: str = "內容") -> Path:
    lines = ["# 標題", ""]
    if kind is not None:
        lines.append(f"brief-kind: {kind}")
    lines += ["", body, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _sot_kinds() -> dict[str, object]:
    return json.loads(LIFECYCLE.read_text(encoding="utf-8"))["kinds"]


# ---------------------------------------------------------------------------
# 判準本體
# ---------------------------------------------------------------------------


def test_classification_follows_sot_for_every_kind(tmp_path: Path) -> None:
    """🔴 對 SoT 中的**每一個** kind 都驗，且期望值由 SoT 導出而非寫死。

    寫死期望值＝在測試裡複製第二份判準；SoT 改了測試不會紅，等於沒有看守。
    """
    kinds = _sot_kinds()
    assert kinds, "SoT kinds 為空 ⇒ 本測空轉"
    for kind, entry in kinds.items():
        want = (
            "findings"
            if entry.get("produces_findings") is True
            else "non-findings"
            if entry.get("produces_findings") is False
            else "unknown"
        )
        f = _brief(tmp_path / f"{kind}.md", kind)
        got = _run(["--single", str(f)])
        assert got.returncode == 0, got.stderr
        assert got.stdout.strip() == want, f"{kind}: want={want} got={got.stdout!r}"


def test_false_kinds_are_non_findings_not_unknown(tmp_path: Path) -> None:
    """🔴 `produces_findings=false` 必須判 `non-findings`，**不是** `unknown`。

    這是 jq `//` 陷阱的正向斷言：`false // "unknown"` 在 jq 回傳 "unknown"
    （`jq -n 'false // "u"'` → `"u"`），凍結 TODO:1068 的偽碼正是那樣寫的
    ⇒ 逐字照抄會讓 impl／stamp **靜默**誤判成 unknown。
    """
    falses = [k for k, v in _sot_kinds().items() if v.get("produces_findings") is False]
    assert falses, "SoT 無 produces_findings=false 的 kind ⇒ 本測空轉"
    for kind in falses:
        f = _brief(tmp_path / f"{kind}.md", kind)
        assert _run(["--single", str(f)]).stdout.strip() == "non-findings", kind


def test_mut_jq_slash_slash_regresses_false_kinds(tmp_path: Path) -> None:
    """MUT-a：把判準換回凍結 TODO 偽碼的 `//` 寫法 → false kind 轉 unknown（承重）。"""
    src = CLASSIFY.read_text(encoding="utf-8")
    anchor = """        (.kinds[$k] // {}) as $e
        | if ($e | has("produces_findings")) and (($e.produces_findings | type) == "boolean")
          then ($e.produces_findings | tostring)
          else "unknown"
          end"""
    assert anchor in src, "MUT-a 錨點漂移：has() 判準"
    mut = tmp_path / "mut_a.sh"
    mut.write_text(
        src.replace(anchor, '(.kinds[$k].produces_findings // "unknown") | tostring', 1),
        encoding="utf-8",
    )
    f = _brief(tmp_path / "stamp.md", "stamp")
    assert _run(["--single", str(f)]).stdout.strip() == "non-findings"
    assert (
        _run(["--single", str(f)], script=mut, lifecycle=LIFECYCLE).stdout.strip()
        == "unknown"
    )


def test_mut_wrong_sot_field_name_makes_everything_unknown(tmp_path: Path) -> None:
    """MUT-b：把欄位名換成凍結 TODO 偽碼的 `is_findings_kind` → 全部轉 unknown（承重）。

    該鍵在 SoT 中**不存在**（`jq 'keys'` 實測）——這也是靜默失敗：不報錯，只是全 unknown。
    """
    src = CLASSIFY.read_text(encoding="utf-8")
    assert src.count("produces_findings") >= 2, "MUT-b 錨點漂移：欄位名"
    mut = tmp_path / "mut_b.sh"
    mut.write_text(src.replace("produces_findings", "is_findings_kind"), encoding="utf-8")
    for kind in ("review", "stamp"):
        f = _brief(tmp_path / f"{kind}.md", kind)
        assert _run(["--single", str(f)]).stdout.strip() != "unknown"
        assert (
        _run(["--single", str(f)], script=mut, lifecycle=LIFECYCLE).stdout.strip()
        == "unknown"
    )


def test_no_brief_kind_is_unknown_not_guessed(tmp_path: Path) -> None:
    """SPEC 邊界 ③：沒有 `brief-kind:` 宣告 ⇒ `unknown`，**不得猜**。"""
    f = _brief(tmp_path / "none.md", None, body="# review 之類的字眼不得被用來猜")
    assert _run(["--single", str(f)]).stdout.strip() == "unknown"


def test_unregistered_kind_is_unknown(tmp_path: Path) -> None:
    """SoT 沒登記的 kind ⇒ unknown（fail-closed，不 fallback）。"""
    f = _brief(tmp_path / "weird.md", "definitely-not-a-kind")
    assert _run(["--single", str(f)]).stdout.strip() == "unknown"


def test_malformed_kind_value_is_unknown(tmp_path: Path) -> None:
    """值黏了標點（語料中實際存在 8 例）⇒ unknown。

    「看起來像 consult」不足以判成 consult —— 正規化就是猜（SPEC 邊界 ③ 禁止）。
    """
    for bad in ("consult;", "consult；scope=read-only", "review;"):
        f = _brief(tmp_path / "m.md", bad)
        assert _run(["--single", str(f)]).stdout.strip() == "unknown", bad


def test_kind_whitelist_is_not_hardcoded(tmp_path: Path) -> None:
    """🔴 SoT 加一個新 kind ⇒ 分類器**不改一行**就跟著走。

    SPEC 明令「禁在腳本內再硬編碼 kind 白名單或 fallback」；
    本測是那條禁令的機械看守。
    """
    sot = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    sot["kinds"]["brandnewkind"] = {"produces_findings": True}
    alt = tmp_path / "alt_lifecycle.json"
    alt.write_text(json.dumps(sot, ensure_ascii=False), encoding="utf-8")
    f = _brief(tmp_path / "n.md", "brandnewkind")
    assert _run(["--single", str(f)]).stdout.strip() == "unknown"  # 真 SoT 沒有
    assert _run(["--single", str(f)], lifecycle=alt).stdout.strip() == "findings"


# ---------------------------------------------------------------------------
# fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    ["", "{}", '{"kinds": []}', '{"kinds": {}}', "not json at all"],
    ids=range(5),
)
def test_broken_sot_fails_closed(tmp_path: Path, content: str) -> None:
    """SoT 缺失／壞掉／無 .kinds 物件 ⇒ rc≠0，不得靜默給答案。"""
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    f = _brief(tmp_path / "x.md", "review")
    got = _run(["--single", str(f)], lifecycle=bad)
    assert got.returncode != 0, f"壞 SoT 竟然 rc=0: {content!r}"
    assert "FINDINGS-KIND FAIL" in got.stderr


def test_missing_sot_fails_closed(tmp_path: Path) -> None:
    f = _brief(tmp_path / "x.md", "review")
    got = _run(["--single", str(f)], lifecycle=tmp_path / "nope.json")
    assert got.returncode != 0 and "FINDINGS-KIND FAIL" in got.stderr


def test_no_mode_fails_closed() -> None:
    got = _run([])
    assert got.returncode != 0 and "FINDINGS-KIND FAIL" in got.stderr


# ---------------------------------------------------------------------------
# --audit
# ---------------------------------------------------------------------------


def test_audit_on_real_corpus_rc0() -> None:
    """SPEC ASSERT：`--audit --corpus handoffs` THEN rc=0。"""
    got = _run(["--audit", "--corpus", "handoffs"])
    assert got.returncode == 0, got.stderr
    assert "分母（實際掃描檔數，現跑導出）=" in got.stdout
    assert "# 分類小計" in got.stdout


def test_audit_denominator_is_computed_not_literal(tmp_path: Path) -> None:
    """分母須現跑導出：語料多一個檔，分母就 +1。"""
    corpus = tmp_path / "c"
    corpus.mkdir()
    _brief(corpus / "a.md", "review")
    first = _run(["--audit", "--corpus", str(corpus)]).stdout
    assert "=1" in first
    _brief(corpus / "b.md", "impl")
    assert "=2" in _run(["--audit", "--corpus", str(corpus)]).stdout


def _audit_pairs(corpus: Path) -> list[tuple[str, str]]:
    """從 --audit 的明細區取出 (brief-kind, 分類) 逐列。"""
    out = _run(["--audit", "--corpus", str(corpus)]).stdout
    body = out.split("檔數", 1)[1].split("# 分類小計", 1)[0]
    pairs: list[tuple[str, str]] = []
    for line in body.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1].isdigit():
            pairs += [(parts[0], parts[1])] * int(parts[-1])
    return sorted(pairs)


def test_audit_agrees_with_single_file_by_file(tmp_path: Path) -> None:
    """🔴 `--audit`（awk 批次）與 `--single`（grep+jq 逐檔）是**兩條程式路徑**。

    〔`COMPOSER-R1-P2-01`：原版只比「逐檔加總 vs 小計」，
    兩個檔互換分類而總數不變時會**假綠**。改為逐檔配對比對。〕
    """
    corpus = tmp_path / "c"
    corpus.mkdir()
    for name, kind in {
        "r.md": "review",
        "i.md": "impl",
        "s.md": "stamp",
        "c.md": "consult",
        "z.md": "not-a-kind",
    }.items():
        _brief(corpus / name, kind)
    _brief(corpus / "none.md", None)

    want = sorted(
        (
            (_run(["--single", str(f), "--corpus", str(corpus)]).stdout.strip() or "?")
            and (
                _brief_kind_or_dash(f),
                _run(["--single", str(f), "--corpus", str(corpus)]).stdout.strip(),
            )
        )
        for f in sorted(corpus.glob("*.md"))
    )
    assert _audit_pairs(corpus) == want


def _brief_kind_or_dash(f: Path) -> str:
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("brief-kind:"):
            v = line.split(":", 1)[1].strip().split()[0] if line.split(":", 1)[1].strip() else ""
            return v or "-"
    return "-"


def test_audit_and_single_agree_on_crlf(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P1-02`：CRLF 檔在兩條路徑上曾經分歧。

    `brief-kind: review\\r\\n` —— shell 路徑的 `awk '{print $2}'` 會得到 `review\\r`
    （awk 預設 FS 不含 `\\r`）⇒ 查 SoT 失敗判 unknown；
    awk 批次路徑的 `sub(/[[:space:]].*$/,"",k)` 卻會把 `\\r` 當空白剝掉 ⇒ 判 findings。
    ⇒ `--audit` 的矩陣不代表 `--single` 的行為。修法＝兩條路徑都先剝 CR。
    """
    corpus = tmp_path / "c"
    corpus.mkdir()
    (corpus / "crlf.md").write_bytes(b"# t\r\nbrief-kind: review\r\n\r\nbody\r\n")
    single = _run(["--single", str(corpus / "crlf.md")]).stdout.strip()
    assert single == "findings", f"CRLF 檔 --single 判成 {single}"
    assert _audit_pairs(corpus) == [("review", "findings")]


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P1-02`：受測檔不存在 ⇒ rc≠0。

    原本靜默回 `unknown` rc=0，呼叫端分不出「這檔沒宣告」與「這檔根本不在」。
    """
    got = _run(["--single", str(tmp_path / "nope.md")])
    assert got.returncode != 0 and "FINDINGS-KIND FAIL" in got.stderr


# ---------------------------------------------------------------------------
# brief↔產出 導出（COMPOSER-R1-P1-01 裁定 (B)：本票內補）
# ---------------------------------------------------------------------------


def test_output_inherits_kind_from_sibling_brief(tmp_path: Path) -> None:
    """委員產出檔不帶 `brief-kind:`，但可由**同輪 brief** 導出。

    `committee_run.sh` 以 `<out前綴>-<family>.md` 產出交件檔，
    而 `<out前綴>` 即 brief 的 session 前綴 ⇒ 兩者關聯是工具**機械產生**的，
    不是命名慣例，故此為導出而非猜測。
    """
    c = tmp_path / "c"
    c.mkdir()
    _brief(c / "20260810-x-review-r1-brief.md", "review")
    (c / "20260810-x-review-r1-codex.md").write_text("# 報告\n無宣告\n", encoding="utf-8")
    (c / "20260810-x-review-r1-composer.md").write_text("# 報告\n", encoding="utf-8")

    for fam in ("codex", "composer"):
        f = c / f"20260810-x-review-r1-{fam}.md"
        assert _run(["--single", str(f)]).stdout.strip() == "unknown"  # 無語料 ⇒ 不導出
        assert (
            _run(["--single", str(f), "--corpus", str(c)]).stdout.strip() == "findings"
        ), fam


def test_derivation_prefers_longest_session_prefix(tmp_path: Path) -> None:
    """兩個 session 前綴互為前綴時，取**最長**匹配（避免張冠李戴）。"""
    c = tmp_path / "c"
    c.mkdir()
    _brief(c / "20260810-x-brief.md", "review")
    _brief(c / "20260810-x-r2-brief.md", "impl")
    (c / "20260810-x-r2-codex.md").write_text("# 報告\n", encoding="utf-8")
    assert (
        _run(["--single", str(c / "20260810-x-r2-codex.md"), "--corpus", str(c)])
        .stdout.strip()
        == "non-findings"
    )


def test_derivation_does_not_apply_to_unrelated_files(tmp_path: Path) -> None:
    """前綴對不上的檔不得被導出（不得因為「同一個目錄」就套用）。"""
    c = tmp_path / "c"
    c.mkdir()
    _brief(c / "20260810-x-review-r1-brief.md", "review")
    (c / "完全無關的筆記.md").write_text("# n\n", encoding="utf-8")
    assert (
        _run(["--single", str(c / "完全無關的筆記.md"), "--corpus", str(c)])
        .stdout.strip()
        == "unknown"
    )


# ---------------------------------------------------------------------------
# --sample（誤擋率 receipt 的抽樣必須可重現）
# ---------------------------------------------------------------------------


def test_sample_is_deterministic_and_seed_sensitive() -> None:
    a = _run(["--sample", "--corpus", "handoffs", "--n", "40", "--seed", "7"]).stdout
    b = _run(["--sample", "--corpus", "handoffs", "--n", "40", "--seed", "7"]).stdout
    c = _run(["--sample", "--corpus", "handoffs", "--n", "40", "--seed", "8"]).stdout
    assert a == b, "同 seed 不可重現 ⇒ receipt 無法被複驗"
    assert a != c, "換 seed 結果相同 ⇒ seed 沒有作用（抽樣可能是固定順序）"


def test_sample_is_not_filename_ordered() -> None:
    """🔴 抽樣不得等價於「檔名排序取前 N」。

    檔名帶日期與 session ⇒ 前綴排序會系統性偏向早期輪次，
    那樣抽出來的誤擋率不代表母體。
    """
    got = [
        ln.split("\t")[2]
        for ln in _run(
            ["--sample", "--corpus", "handoffs", "--n", "30", "--seed", "1"]
        ).stdout.splitlines()
        if ln.strip()
    ]
    assert len(got) == 30
    naive = sorted(str(p) for p in Path(REPO_ROOT / "handoffs").glob("*.md"))[:30]
    assert got != naive, "抽樣結果等於檔名排序前 N ⇒ 有系統性偏差"


def test_sample_n_larger_than_corpus_returns_all(tmp_path: Path) -> None:
    corpus = tmp_path / "c"
    corpus.mkdir()
    for i in range(3):
        _brief(corpus / f"{i}.md", "review")
    out = _run(["--sample", "--corpus", str(corpus), "--n", "99"]).stdout
    assert len([x for x in out.splitlines() if x.strip()]) == 3


# ---------------------------------------------------------------------------
# --wilson（§V-FP 的區間必須算對）
# ---------------------------------------------------------------------------


def test_wilson_reproduces_spec_numbers() -> None:
    """🔴 用 SPEC §V-FP 自己算出的兩個數字當 oracle。

    SPEC 主張 0-FP 時上界：n=50 → 7.14%（不可能過關）、n=100 → 3.70%（可過關），
    並據此把抽樣下限由 50 改成 100。若本實作算不出這兩個數，
    那條「n≥100」的決定就失去依據。
    """
    got50 = _run(["--wilson", "--fp", "0", "--n", "50"]).stdout
    got100 = _run(["--wilson", "--fp", "0", "--n", "100"]).stdout
    assert "7.13" in got50 or "7.14" in got50, got50
    assert "3.69" in got100 or "3.70" in got100, got100


def test_wilson_reports_interval_not_point_estimate() -> None:
    """§V-FP 明令：報區間不報點估計，禁寫「誤擋率 0%」。"""
    out = _run(["--wilson", "--fp", "0", "--n", "100"]).stdout
    assert "95% CI = [" in out and "%," in out
    assert out.count("%") >= 3


def test_wilson_rejects_bad_inputs() -> None:
    for args in (["--fp", "5", "--n", "3"], ["--fp", "-1", "--n", "10"], ["--fp", "0", "--n", "0"]):
        got = _run(["--wilson", *args])
        assert got.returncode != 0, args


# ---------------------------------------------------------------------------
# G-1：本 Task 不得有 caller
# ---------------------------------------------------------------------------


def test_classifier_has_no_caller_yet() -> None:
    """🔴 Task 4.1 只產判準**不改判**：本檔不得被任何既有腳本呼叫。

    有 caller ⇒ 行為可能已被改動 ⇒ G-1 的「rc 不得由 0 變非 0」失去保證。
    Task 4.2 才接。

    🔴 判準是「**被執行**」而非「被提及」——`govb1_final_gate.sh` 把本檔列為
    G-3 的**掃描標的**（查有無 `--dry-run` 之類的逃生口），那是被讀不是被呼叫。
    用「出現字串就算 caller」會把那種列舉誤判成違規，故判準定義為：
    緊接在 `bash`／`sh`／`.`／`source` 之後（可帶路徑前綴）才算呼叫。
    """
    import re

    invoke = re.compile(
        r"(?:^|[;&|`(]|\$\()\s*(?:bash|sh|\.|source)\s+\S*findings_kind_classify\.sh"
    )
    # 🔴 `CODEX-R1-P1-05`：原版只掃 `scripts/*.sh` 與**根目錄** `git_hooks/`，
    #   漏了實際存在的 `scripts/git_hooks/` ⇒ 掛在那裡的 caller 可靜默通過。
    #   改為遞迴掃描 scripts/ 全部檔案 ＋ 任一層的 git_hooks 目錄。
    targets = [p for p in (REPO_ROOT / "scripts").rglob("*") if p.is_file()]
    for hooks in (REPO_ROOT / "git_hooks", REPO_ROOT / "scripts" / "git_hooks"):
        if hooks.is_dir():
            targets += [p for p in hooks.rglob("*") if p.is_file()]
    hits: list[str] = []
    for p in sorted(targets):
        if p.name == CLASSIFY.name:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if invoke.search(line):
                hits.append(f"{p.relative_to(REPO_ROOT)}:{i}")
    assert not hits, f"Task 4.1 階段不得有 caller: {hits}"


def test_no_caller_probe_is_falsifiable(tmp_path: Path) -> None:
    """🔴 上一條的判準本身要可證偽：真的放一行呼叫進去，它必須抓到。

    否則「零 caller」可能只是正則永遠不命中。
    """
    import re

    invoke = re.compile(
        r"(?:^|[;&|`(]|\$\()\s*(?:bash|sh|\.|source)\s+\S*findings_kind_classify\.sh"
    )
    positives = [
        "bash scripts/findings_kind_classify.sh --audit --corpus handoffs",
        '  . "${SCRIPT_DIR}/findings_kind_classify.sh"',
        "out=$(bash scripts/findings_kind_classify.sh --single x)",
    ]
    negatives = [
        "        scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/x.sh 2>/dev/null; }",
        "# 見 scripts/findings_kind_classify.sh",
    ]
    for s in positives:
        assert invoke.search(s), f"應判為 caller 卻沒抓到: {s!r}"
    for s in negatives:
        assert not invoke.search(s), f"不該判為 caller 卻抓到: {s!r}"


def test_script_is_executable_and_syntax_clean() -> None:
    assert CLASSIFY.is_file()
    assert shutil.which("jq"), "jq 缺失 ⇒ 分類器無法驗"
    got = subprocess.run(
        ["bash", "-n", str(CLASSIFY)], capture_output=True, text=True, check=False
    )
    assert got.returncode == 0, got.stderr
