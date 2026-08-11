"""測試沙箱之角色名冊釘定（票 B-49 修法之單一定義處）。

為何存在（2026-08-11）：
    多個治理測試要驗「`brief-kind=impl` 走 CLI 派工時的行為」。角色閘規定
    impl 的目標家族必須 == `implementer`，於是這些測試**直接耦合到生產名冊**：
    有的寫死 `grok`，有的「正確地」從 SoT 讀 `implementer` 再餵給 CLI。

    使用者 2026-08-11 把 `implementer` 改成 `claude`（編排端自任實作）後，
    **兩種寫法都紅**，而且是**兩種不同的紅**：
      形態 A（寫死）  ：`test_result_state_format_failed.py`
                        → 角色閘拒：「實作端須為 claude,但收到 grok」
      形態 B（讀 SoT）：`test_rolegate_predispatch.py`／`test_stamp_taskid_inject.py`
                        → `cx_run.sh` 家族白名單拒：「family 須為 codex|grok|composer, 得到: claude」

    🔴 形態 B 是重點：那些測試已經在做「讀 SoT」這件對的事，**仍然紅**。
    因為 `claude` 沒有 CLI 配方——編排端自任實作時，`impl` 根本不對外派工。
    ⇒ 「把測試改成讀 SoT」**不是**這批紅的修法，對 3 條中的 2 條是錯的。

修法：
    這些測試要驗的是 **`cx_run.sh`／`committee_run.sh` 在 impl 路徑上的行為**，
    與「現實世界誰是 implementer」無關。故在**沙箱副本**內把名冊釘成一個
    有 CLI 配方的家族，測試即與生產名冊解耦，日後換誰實作都不再回紅。

🔴 邊界（不得逾越）：
    本模組**只讀寫傳入的 `scripts_dir`**，且該目錄若解析到 repo 真實 `scripts/`
    即 fail-closed 拒絕。repo 的 `scripts/governance_roles.json` 是使用者專屬 SoT，
    任何測試都不得寫它。

🔴 票 B-49 閉合條件 3「`eligible` 與測試內家族集合須**機械連動**（禁再硬編三元組）」：
    本模組**不得**出現 `("codex", "grok", "composer")` 這種字面三元組。
    合法家族一律由 SoT 導出，並與 `cx_run.sh` 的實際 dispatch 分支**交叉比對**——
    兩者漂移即 fail-closed 轉紅（同一概念兩處定義不一致，是本 repo 反覆發生的病）。

🔴 review r4 修掉的三個自傷（`CODEX-R4-P1-03`／`CODEX-R4-P1-04`）：
    ① `reviewers` 公式原寫 `eligible − {impl}` ⇒ 會把**無 CLI 配方的 `claude`**
       算進 reviewers。正確公式在 `scripts/set_roles.sh`：`eligible ∩ review_families − {impl}`。
       🔴 這個公式在本 session **第三次**咬人（set_roles.sh 一次、本檔一次、本檔 review 一次），
       故此處逐字註明出處，不再靠記憶。
    ② SoT 來源原固定讀 `REPO_ROOT/scripts/*`，**不是**傳入的 `scripts_dir`
       ⇒ 沙箱內對名冊／`cx_run.sh` 的變異**看不見**，mutation 測試會假綠。
    ③ dispatch 分支的 regex 原要求**恰好兩個空白**縮排 ⇒ codex 以探針證明
       四空白的 `evil)` 分支（確實含 `_prepare_and_run`）會被漏掉。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_PRODUCTION_SCRIPTS = (REPO_ROOT / "scripts").resolve()

# `cx_run.sh` 真正決定「這個家族派不派得出去」的那個 case 區塊；
# 以 dispatch 動作（而非錯誤訊息字串）為錨點——訊息會被改寫，分支不會。
_DISPATCH_ACTION = "_prepare_and_run"

# case 分支列：**任意**縮排（含 0）。原本釘死兩個空白，四空白分支會被漏掉。
_CASE_ARM_RE = re.compile(r"^[ \t]*([a-z][a-z0-9-]*)\)", re.M)


def _require_sandbox(scripts_dir: Path) -> Path:
    """拒絕對生產 `scripts/` 動手。呼叫端誤傳即當場紅，不靠紀律。"""
    d = Path(scripts_dir).resolve()
    if d == _PRODUCTION_SCRIPTS:
        raise AssertionError(
            f"拒絕操作生產 scripts 目錄：{d}\n"
            "本模組只准改測試沙箱副本；repo 的 governance_roles.json 是使用者專屬 SoT。"
        )
    return d


def cli_dispatchable_families(scripts_dir: Path) -> tuple[str, ...]:
    """回傳「有 CLI 配方、派得出去」的家族，由 `scripts_dir` 導出並交叉比對。

    兩個獨立來源（**皆讀 `scripts_dir`**，故沙箱內的變異看得見）：
      ① `governance_families.json` 的 `review_families`
         ——SoT 中「會被派工的委員家族」。`claude`（編排端，無 CLI）與
         `agy`（`advisory_only`，唯讀）皆不在其中。
      ② `cx_run.sh` 中含 `_prepare_and_run` 的 `case` 分支
         ——實際放行哪些家族的**執行期真相**。

    兩者不一致 ⇒ `AssertionError`（fail-closed）。這正是本 repo 反覆出事的
    「同一概念兩處定義不一致」，故做成偵測器而非任一方的附庸。
    """
    d = _require_sandbox(scripts_dir)

    sot_path = d / "governance_families.json"
    if not sot_path.is_file():
        raise AssertionError(f"沙箱缺家族 SoT：{sot_path}（fail-closed）")
    sot = json.loads(sot_path.read_text(encoding="utf-8"))
    from_sot = sot.get("review_families")
    if not isinstance(from_sot, list) or not from_sot:
        raise AssertionError(f"家族 SoT 缺 review_families 或型別錯：{from_sot!r}（fail-closed）")

    cx_path = d / "cx_run.sh"
    if not cx_path.is_file():
        raise AssertionError(f"沙箱缺派工腳本：{cx_path}（fail-closed）")
    src = cx_path.read_text(encoding="utf-8")
    # 🔴 區塊結尾須容許縮排的 `esac`。原本寫 `\nesac`（頂格）⇒ `cx_run.sh:727` 的
    #    `    esac` 不匹配，整個吞掉 `_prepare_and_run` 內層 case（:699）與外層
    #    dispatch case（:840）兩塊，家族名各出現兩次。
    #    舊版之所以「看起來對」，純粹是因為兩塊縮排剛好不同（內層 6 空白、外層 2 空白），
    #    而舊 regex 恰好只收 2 空白 ⇒ **靠巧合正確**。此為 `CODEX-R4-P1-04` 之實質。
    blocks = [
        b
        for b in re.findall(r'case\s+"\$\{fam\}"\s+in\n(.*?)\n[ \t]*esac', src, re.S)
        if _DISPATCH_ACTION in b
    ]
    if len(blocks) != 1:
        raise AssertionError(
            f"在 cx_run.sh 找到 {len(blocks)} 個含 {_DISPATCH_ACTION} 的家族 case 區塊，"
            "預期恰好 1 個 ⇒ 錨點失配，拒絕猜測（fail-closed）"
        )
    from_src = _CASE_ARM_RE.findall(blocks[0])
    if not from_src:
        raise AssertionError("cx_run.sh 家族 case 區塊抽不到任何分支 ⇒ 錨點失配（fail-closed）")

    if sorted(from_sot) != sorted(from_src):
        raise AssertionError(
            "家族清單漂移（fail-closed）：\n"
            f"  governance_families.json review_families = {sorted(from_sot)}\n"
            f"  cx_run.sh dispatch 分支              = {sorted(from_src)}\n"
            "兩處定義同一概念，必須一致。"
        )
    return tuple(sorted(from_sot))


def pin_implementer(scripts_dir: Path, fam: str | None = None) -> str:
    """把沙箱名冊的 implementer 釘成 `fam`（預設取合法集合之首），回傳該值。

    `reviewers` 依 `scripts/set_roles.sh` 之公式重算：
    **`eligible ∩ review_families − {implementer}`**——不是 `eligible − {implementer}`
    （後者會把無 CLI 配方的編排端算進 review pool）。
    """
    d = _require_sandbox(scripts_dir)
    allowed = cli_dispatchable_families(d)
    if fam is None:
        fam = allowed[0]
    if fam not in allowed:
        raise AssertionError(
            f"釘定家族 {fam!r} 無 CLI 配方 ⇒ impl 派工必被 cx_run.sh 家族白名單拒；"
            f"合法值：{allowed}"
        )
    roles = d / "governance_roles.json"
    if not roles.is_file():
        raise AssertionError(f"沙箱缺角色 SoT：{roles} ⇒ 釘定無意義（fail-closed）")
    rd = json.loads(roles.read_text(encoding="utf-8"))
    eligible = rd.get("eligible")
    if not isinstance(eligible, list) or fam not in eligible:
        raise AssertionError(f"釘定家族 {fam!r} 不在 eligible={eligible!r}（fail-closed）")

    reviewers = sorted(f for f in eligible if f in allowed and f != fam)
    if len(reviewers) < 2:
        raise AssertionError(
            f"釘 {fam!r} 後 review pool 只剩 {reviewers} ⇒ 兩家 review 鐵律當場破（fail-closed）"
        )
    rd["implementer"] = fam
    rd["reviewers"] = reviewers
    rd["_pinned_by_test"] = "tests/governance/_role_pin.py"
    roles.write_text(json.dumps(rd, ensure_ascii=False, indent=2), encoding="utf-8")
    return fam
