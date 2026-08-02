"""P16-GATE-D1-STRUCTURED-VERDICT：`gate.sh` D-1 的 Verdict 檢查必須驗「已填實」。

出生事故（兩次，皆實證）：
  ①`Verdict（綜合）：結論` —— Verdict 與冒號間插字 → 舊正則不中 → **誤拒**。
    代價特別高：改 body 會讓已取得的三家戳記 sha 全失效，整輪重簽。
  ②`**Verdict: （待填…）**` 佔位行 → 舊正則**命中** ⇒ 沒填結論也拿得到 token
    （`CODEX-R2-P1-13`，端到端實跑 GATE PASS rc=0）＝**真 fail-open**。

2026-08-02 實測 `handoffs/` 全體語料後發現破口比原記載更大：
canonical 範本自己那行 `## Verdict：{{可派工 / 需修補後派工 / 有根本缺陷需重作}}`
出現 **88 次**且命中舊正則 ⇒ **複製範本未填即可過閘**。

本檔跑**真正的 `scripts/gate.sh`**（非副本），故測到的是上線行為。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"


def _run_gate(adversarial: str) -> subprocess.CompletedProcess[str]:
    """高風險 dispatch + --adversarial；token/audit 落隔離目錄，不汙染真實 gate dir。

    ⚠️ 用 `TemporaryDirectory` 而非 `mkdtemp`（`CODEX-R1-P2-03`）：
       `mkdtemp` 不自動清除，跑一次全套會在系統 tmp 留下數十個目錄。
    """
    with tempfile.TemporaryDirectory(prefix="gate_verdict_test_") as gate_tmp:
        return _dispatch(adversarial, gate_tmp)


def _dispatch(adversarial: str, gate_tmp: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, GATE_DIR_OVERRIDE=gate_tmp)
    argv = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "D-1 structured verdict test",
        "--risk",
        "high",
        "--facts-asked",
        "none-needed:unit test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:D-1 structured verdict test",
        "--adversarial",
        adversarial,
    ]
    return subprocess.run(
        argv, cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env
    )


@pytest.fixture()
def adv_factory():
    """產生**能走到 Verdict 檢查**的 adversarial fixture，用完刪除。

    ⚠️ 兩道前置否則會「紅錯原因」（第一版就是這樣寫錯的）：
      1. `gate.sh:375` 要求 `^handoffs/.*-ADV-(CODEX|COMPOSER|GROK)\\.md$`——
         **repo 相對路徑**且特定命名，否則走 reconcile 戳記路徑並以
         「既非 ADV 命名亦未獲 reconcile 戳記核可」拒發 ⇒ 所有案例都紅，
         但紅的原因與 Verdict 無關，測試等於在測空氣。
      2. 內容不得含 `[BLOCKING]` 或 `ID: ADV-…`，否則 D-2 要求 `--reconcile` 必填，
         同樣使結果不取決於 Verdict。
    故 fixture 落在 repo 的 `handoffs/`（該目錄本就不進版控），測完刪除。
    """
    created: list[Path] = []

    counter = [0]

    def _make(verdict_line: str, tag: str = "") -> str:
        # ⚠️ 回傳 **repo 相對路徑字串**：`gate.sh:375` 的判定是
        #    `^handoffs/.*-ADV-(FAMS)\\.md$`，傳絕對路徑不命中 ⇒ 落入 reconcile 戳記路徑而誤拒。
        counter[0] += 1
        name = f"pytest-verdict-{os.getpid()}-{counter[0]}-ADV-CODEX.md"
        p = REPO_ROOT / "handoffs" / name
        p.write_text(f"# 對抗審查\n\n一些內容。\n\n{verdict_line}\n", encoding="utf-8")
        created.append(p)
        return f"handoffs/{name}"

    yield _make
    for p in created:
        p.unlink(missing_ok=True)


# ───────────────────────── 應被擋（舊判準會放行者標「回歸」）─────────────────────────


@pytest.mark.parametrize(
    ("label", "line"),
    [
        # 舊判準**放行**的三種——本票主要修的就是它們
        ("回歸:canonical 範本 {{}} 佔位", "## Verdict：{{可派工 / 需修補後派工 / 有根本缺陷需重作}}"),
        ("回歸:事故②佔位行", "**Verdict: （待填…）**"),
        ("回歸:散文中順口提及", "本節說明 reviewer 的 Verdict: 應該怎麼寫"),
        # 舊判準已擋、須維持
        ("骨架未填行", "**Verdict** ← 未填。填寫時整行改寫為「Verdict」＋半形冒號＋結論"),
        ("只有標題無冒號", "## Verdict"),
        ("冒號後空白", "## Verdict："),
        ("冒號後只有省略號", "## Verdict：…"),
        ("冒號後 TBD", "Verdict: TBD"),
        # 放寬 list 前綴（CODEX-R1-P1-01）後的迴歸護欄：不得順手把散文的洞打開。
        # `>` 刻意**不列入**允許前綴——全語料中 `>` 開頭含 Verdict 的行全是散文提及。
        ("blockquote 前綴不得放行", "> 當時的 Verdict: 可派工（僅為引述歷史）"),
        ("表格列不得放行", "| 項目 | Verdict: 可合併 |"),
        ("散文行末黏貼 heading", "如前所述## Verdict：可合併"),
        # CODEX-R2-P2-02：前三條都不是**精確** quote 形，未來放寬 marker 時擋不住重開散文洞
        ("精確 blockquote", "> Verdict: APPROVE"),
        ("精確 blockquote + 粗體", "> **Verdict**: 可合併"),
        # CODEX-R2-P2-01：`[#*+-]+` 貪吃整串使分隔線殘留被當合法填實
        ("分隔線殘留（---）", "--- Verdict: APPROVE"),
        ("分隔線殘留（----）", "---- Verdict: APPROVE"),
        ("marker 後無空白不算清單", "-Verdict: APPROVE"),
        # 註：**刻意不測「結論太短」**。兩次事故皆與長度無關，無事故支撐即不立規則；
        #     且長度規則會誤拒 `Verdict: OK`／`Verdict: 過`（見 gate.sh 該處註解）。
    ],
)
def test_unfilled_verdict_rejected(adv_factory, label: str, line: str) -> None:
    r = _run_gate(adv_factory(line, label))
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"[{label}] 未填的 Verdict 竟拿到 token ＝ fail-open\n{out}"
    # ⚠️ 必須確認**紅在 Verdict 這一關**，否則可能紅在 ADV 命名／reconcile 戳記等別的前置
    assert "缺**已填實的** Verdict 行" in out, (
        f"[{label}] 有拒發但**不是 Verdict 這一關**擋的 ⇒ 該案例沒測到本票的守衛\n{out}"
    )


# ───────────────────────── 應放行 ─────────────────────────


@pytest.mark.parametrize(
    ("label", "line"),
    [
        ("標準 heading 全形冒號", "## Verdict：需修補後派工"),
        ("標準 heading 半形冒號", "## Verdict: 可合併"),
        ("粗體 + 冒號", "**Verdict**: 不可合併。三家皆判不可進入實作。"),
        ("裸行", "Verdict: APPROVE"),
        # 事故①：Verdict 與冒號間有括號補充，舊判準**誤拒**
        ("事故①:括號補充(全形)", "Verdict（綜合）：可合併"),
        ("事故①:括號補充(半形)", "Verdict(綜合): 可合併"),
        ("結論帶括號補充", "## Verdict：需修補後派工（極輕量）"),
        ("英文結論", "**Verdict: CLOSED**"),
        # CODEX-R1-P1-01：第一版只剝 `#*` 與空白 ⇒ list 前綴的實填 Verdict 被誤拒。
        # 全語料實測有 25 個 bullet 形、3 個 ordered 形。誤拒代價＝整輪重簽戳記。
        ("bullet 前綴（-）", "- Verdict: APPROVE"),
        ("bullet 前綴（+）", "+ Verdict: 可合併"),
        ("ordered 前綴（N.）", "4. Verdict: APPROVE"),
        ("ordered 前綴（N)）", "4) Verdict: 可派工"),
        ("巢狀縮排 bullet + 粗體", "  - **Verdict**: 需修補後派工"),
        # codex 實跑確認：first-colon 規則不會截斷含冒號的結論
        ("結論內含冒號", "Verdict: 說明（含冒號：的內容）"),
    ],
)
def test_filled_verdict_accepted(adv_factory, label: str, line: str) -> None:
    """判準＝**Verdict 這一關沒擋它**，而非整個 gate 放行。

    誠實邊界：`gate.sh` 在 Verdict 檢查**之後**還有 provenance 關卡
    （ADV 命名的檔須有對應 `committee_dispatch` 審計事件）。要讓整條 dispatch 回 0
    得偽造 audit 事件——那既昂貴又等於在測試裡繞過稽核鏈，**不做**。
    故此處只斷言「沒有出現 Verdict 的拒發訊息」，這正是本票守衛的作用域。
    """
    r = _run_gate(adv_factory(line, label))
    out = r.stdout + r.stderr
    assert "缺**已填實的** Verdict 行" not in out, (
        f"[{label}] 合法且已填的 Verdict 被 D-1 誤擋"
        f"（改 body 會讓既有三家戳記 sha 失效，代價極高）\n{out}"
    )


# ───────────────────────── mutation：改回舊判準 → 回歸案例轉綠 ─────────────────────────


def test_mutation_restore_loose_regex_turns_red(tmp_path: Path, adv_factory) -> None:
    """把判準改回舊的鬆正則 → `{{…}}` 範本佔位又能過閘。

    這是上面「回歸」案例的可證偽性證明：若不做此變異就無法讓它們放行，
    代表那些測試沒有在測「結構化 Verdict」這件事本身。
    紀律：變異作用在 **tmp 隔離副本**，不動 repo 內 `scripts/gate.sh`。
    """
    import shutil

    iso = tmp_path / "iso"
    (iso / "scripts").mkdir(parents=True)
    for src in (REPO_ROOT / "scripts").iterdir():
        if src.is_file():
            dst = iso / "scripts" / src.name
            shutil.copy2(src, dst)
            if src.suffix == ".sh":
                dst.chmod(0o755)
    gate = iso / "scripts" / "gate.sh"
    text = gate.read_text(encoding="utf-8")
    start = text.find("  if ! awk '")
    end = text.find('    return 1\n  fi\n', start)
    assert start != -1 and end != -1 and start < end, "Verdict 檢查區塊錨點不存在"
    loose = (
        "  if ! grep -qE 'Verdict[[:space:]]*[:：]' \"${adv_file}\"; then\n"
        '    echo "ERROR: MUTATED loose verdict check"\n'
    )
    gate.write_text(text[:start] + loose + text[end:], encoding="utf-8")

    adv = adv_factory("## Verdict：{{可派工 / 需修補後派工 / 有根本缺陷需重作}}", "mut")
    gate_tmp = tmp_path / "gate_dir"   # 走 tmp_path，pytest 自行回收（CODEX-R1-P2-03）
    gate_tmp.mkdir()
    env = dict(os.environ, GATE_DIR_OVERRIDE=str(gate_tmp))
    r = subprocess.run(
        [
            "bash", str(gate), "dispatch",
            "--intent", "mutation loose verdict",
            "--risk", "high",
            "--facts-asked", "none-needed:unit test",
            "--review-role", "single-executor:n/a",
            "--template", "n/a:mutation test",
            "--adversarial", adv,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    out = r.stdout + r.stderr
    assert "缺**已填實的** Verdict 行" not in out, (
        "變異回舊判準後，範本 {{…}} 佔位應**不再被 Verdict 這一關擋下**（重現 fail-open）；"
        f"若仍被擋，表示上面的回歸測試紅的原因不是 Verdict 判準\n{out}"
    )
