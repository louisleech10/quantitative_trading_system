"""產出端覆蓋登記表 — 使用者 2026-08-13 定死之憲法級規則的機械強制點。

使用者逐字：「治理的所有票，包含已經做過和正在做和未來的實作，都要在產出端擋下，
這才能當已完成，除非像 G-7 和 pytest 等可以說明為何不該放在產出端，
這任務完成檢查在所有治理 epic 中都適用，你要想辦法卡住，不能漏。」

🔴 核心卡點＝`test_closed_ticket_without_coverage_is_fail_closed`：
   任何票要標收案，必先登記其檢查掛在哪；掛不到產出端就得寫出為什麼。

🔴 本檔的測試設計紀律（本輪親身教訓）：
   每條反例都必須斷言**目標錯誤訊息**，不能只斷言 rc≠0。
   初版只看 rc，結果核心檢查的 jq 寫錯（`index()` 參數位置的 `.` 已被 pipe 改寫）
   而恆綠，反例卻因 DRIFT 一樣紅 ⇒ **險些把空心檢查當成通過**。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "scripts" / "gen_fact_key_blocks.sh"
REG = REPO / "scripts" / "fact_keys.json"
SETTINGS = REPO / ".claude" / "settings.json"


def _mkrepo(tmp_path: Path, mutate=None) -> Path:
    """複製一棵最小可跑的樹：scripts/ ＋ .claude/settings.json ＋ 全部宿主與 receipt。"""
    root = tmp_path / "r"
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEN, root / "scripts" / GEN.name)
    shutil.copy2(SETTINGS, root / ".claude" / "settings.json")
    # 🔴 掛載點對證會驗「片段對應的腳本在 repo 內存在」⇒ 假 repo 必須備齊被登記的 hook 腳本，
    #    否則基準會因對證失敗而紅（初版漏複製，DRIFT 把真正的錯因蓋掉）。
    for extra in (
        # 🔴 S6.2 ⑪：票全集對帳被接進 --check，故假 repo 也要備齊它與 backlog，
        #    否則該檢查在沙箱一律略過 ⇒ 「刪列繞過」的反例測不出來（等於沒有測試）。
        "ticket_universe.sh",
    ):
        src = REPO / "scripts" / extra
        if src.is_file():
            shutil.copy2(src, root / "scripts" / extra)
    _backlog = REPO / "handoffs" / "20260801-GOV-AMEND-BACKLOG.md"
    if _backlog.is_file():
        (root / "handoffs").mkdir(parents=True, exist_ok=True)
        shutil.copy2(_backlog, root / "handoffs" / _backlog.name)
    data = json.loads(REG.read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(data)
    (root / "scripts" / "fact_keys.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 🔴 檢查 ⑧(b) 會驗「豁免理由／實作位置引用的 <檔>:<行> 存在且非註解」
    #    ⇒ 假 repo 也必須備齊**被引用的檔**，理由與上面備齊 hook 腳本完全相同。
    #    引用集合由註冊表**機械導出**，不寫死清單——寫死會在下次新增引用時再紅一次。
    # 🔴 `.get()` 而非直接索引：部分 mutation 測試會**刪掉** schema 欄位來驗
    #    「整組缺席即 fail-closed」，此處硬索引會讓那些測試死在 fixture 建置而非受測邏輯。
    # 🔴 **掛載點欄也要機械導出**（2026-08-14）：原本被登記的 hook 腳本是**寫死清單**
    #    （factkey_write_guard／doc_format_precheck／gate_check），而同一段註解自己就寫著
    #    「寫死會在下次新增引用時再紅一次」——它防了 `豁免理由` 欄卻沒防 `掛載點` 欄。
    #    實際後果：E-007 改掛 scripts/narrow_check_router.sh 後，沙箱缺該檔 ⇒ 掛載對證失敗
    #    ⇒ `--write` 整個失敗 ⇒ **全部 key 都報 DRIFT，真正的錯因被蓋掉**（推送被擋一次）。
    _roles = data["_schema"].get("enforcement_column_roles") or {}
    for _ek in data["_schema"].get("enforcement_keys") or []:
        if _ek not in data:
            continue
        _cols = data[_ek].get("columns", [])
        for _role, _pat in (("waiver", r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:[0-9]+"),
                            ("mount",  r"[A-Za-z0-9_./-]+\.(?:sh|py)")):
            _name = _roles.get(_role)
            if not _name or _name not in _cols:
                continue
            _ci = _cols.index(_name)
            for _row in data[_ek]["rows"]:
                for _ref in re.findall(_pat, _row[_ci] or ""):
                    _rel = _ref.rsplit(":", 1)[0] if ":" in _ref else _ref
                    # 掛載點欄常只寫 basename（如 `pre-push:gov_check.sh 第 3 段`）
                    if "/" not in _rel:
                        _rel = f"scripts/{_rel}"
                    _src = REPO / _rel
                    _dst = root / _rel
                    if _src.is_file() and not _dst.exists():
                        _dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(_src, _dst)
    # 宿主檔（含空邊界標記）
    # 🔴 同一檔可能是多個 key 的 target（如 GOVERNANCE_EXECUTION_ORDER.md 有三個）
    #    ⇒ 必須**累積**所有標記後一次寫入；逐 key 覆寫只會留下最後一個（初版即如此，基準轉紅）。
    hosts: dict[Path, list[str]] = {}
    for key, val in data.items():
        if key == "_schema":
            continue
        tgts = val["target"]
        for t in ([tgts] if isinstance(tgts, str) else tgts):
            hosts.setdefault(root / t, []).append(key)
    for p, keys in hosts.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        body = "前言\n" + "".join(
            f"<!-- BEGIN GENERATED: {k} -->\n<!-- END GENERATED: {k} -->\n" for k in keys)
        p.write_text(body, encoding="utf-8")
    # opt-in 宿主與 receipt（存在即可）
    for s in data["_schema"].get("mechanism_scope", []):
        p = root / s
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("# 佔位\n", encoding="utf-8")
    roles = data["_schema"].get("mechanism_column_roles", {})
    for mk in data["_schema"].get("mechanism_keys", []):
        ei = data[mk]["columns"].index(roles["evidence"])
        for row in data[mk]["rows"]:
            ev = row[ei]
            if ev.startswith("receipt:"):
                p = root / ev[len("receipt:"):]
                p.parent.mkdir(parents=True, exist_ok=True)
                if not p.exists():
                    p.write_text("佔位\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["bash", str(root / "scripts" / GEN.name), "--write"],
                   cwd=str(root), capture_output=True,
                   env={"PATH": __import__("os").environ["PATH"], "GOVB1_FACTKEY_ROOT": str(root)})
    return root


def _check(root: Path):
    return subprocess.run(
        ["bash", str(root / "scripts" / GEN.name), "--check"],
        cwd=str(root), capture_output=True, text=True,
        env={"PATH": __import__("os").environ["PATH"], "GOVB1_FACTKEY_ROOT": str(root)})


def _enf(data):
    return data[data["_schema"]["enforcement_keys"][0]]


def test_baseline_is_green(tmp_path):
    r = _check(_mkrepo(tmp_path))
    assert r.returncode == 0, r.stderr


def test_mount_must_exist_in_settings_not_self_declared(tmp_path):
    """🔴 檢查 ②：宣告「產出端」必須在 settings.json 對得上，禁自我宣稱。"""
    def m(d):
        _enf(d)["rows"][0][2] = "PostToolUse:Edit,Write:不存在的腳本.sh"
    r = _check(_mkrepo(tmp_path, m))
    assert "禁自我宣稱" in r.stderr, f"自我宣稱未被擋\n{r.stderr}"


def test_mount_matcher_mismatch_is_caught(tmp_path):
    """event 對但 matcher 不對也要擋 —— 掛在別的觸發點不算覆蓋。"""
    def m(d):
        _enf(d)["rows"][0][2] = "PostToolUse:Bash:factkey_write_guard.sh"
    r = _check(_mkrepo(tmp_path, m))
    assert "禁自我宣稱" in r.stderr, r.stderr


def test_waiver_placeholder_is_rejected(tmp_path):
    """檢查 ③：豁免要寫出理由，佔位符不算。"""
    def m(d):
        rows = _enf(d)["rows"]
        idx = next(i for i, row in enumerate(rows) if row[3] != "產出端")
        rows[idx][4] = "TBD"
    r = _check(_mkrepo(tmp_path, m))
    assert "豁免理由為空或佔位符" in r.stderr, r.stderr


def _add_ticket(d, status: str, tid: str = "TEST-TICKET"):
    """在票表**新增**一列（不覆蓋覆蓋表）。

    🔴 刻意自造而非挑現有票：生產資料的票狀態會漂（`B-49` 於本輪即由收案退回），
    依賴它會讓測試在資料變動時靜默失去鑑別力——初版正是如此。
    """
    tk = d["_schema"]["enforcement_ticket_roles"]["key"]
    cols = d[tk]["columns"]
    tr = d["_schema"]["enforcement_ticket_roles"]
    row = ["999"] * len(cols)
    row[cols.index(tr["id"])] = tid
    row[cols.index(tr["status"])] = status
    d[tk]["rows"].append(row)


def test_closed_ticket_without_coverage_is_fail_closed(tmp_path):
    """🔴🔴 核心卡點（檢查 ④）：票標收案但未登記產出端覆蓋 ⇒ 擋下。

    這是使用者「你要想辦法卡住，不能漏」的落法。任何票要收案都得先過這關。
    """
    r = _check(_mkrepo(tmp_path, lambda d: _add_ticket(d, d["_schema"]["enforcement_closed_status"])))
    assert "登記產出端覆蓋" in r.stderr, (
        f"收案票未登記覆蓋卻通過 ⇒ 核心卡點是空心的\n{r.stderr}"
    )
    assert "TEST-TICKET" in r.stderr, f"訊息未指出是哪張票\n{r.stderr}"


def test_non_closed_ticket_does_not_require_coverage(tmp_path):
    """對照組：同一張票不是收案狀態時，不要求登記 —— 證明釘在「收案」而非「所有票」。"""
    r = _check(_mkrepo(tmp_path, lambda d: _add_ticket(d, "部分完成")))
    assert "登記產出端覆蓋" not in r.stderr, (
        f"非收案票也被要求登記 ⇒ 條件釘錯了\n{r.stderr}"
    )


def test_side_enum_is_closed(tmp_path):
    def m(d):
        _enf(d)["rows"][0][3] = "大概有吧"
    r = _check(_mkrepo(tmp_path, m))
    assert "enforcement_side_enum" in r.stderr, r.stderr


@pytest.mark.parametrize("field", [
    "enforcement_keys", "enforcement_side_enum", "enforcement_producer_side",
    "enforcement_column_roles", "enforcement_settings_path",
    "enforcement_closed_status", "enforcement_ticket_roles",
])
def test_schema_fields_are_one_unit(tmp_path, field):
    """schema 為一整組：單獨刪任一欄不得靜默停用四道檢查。"""
    def m(d):
        d["_schema"].pop(field, None)
    r = _check(_mkrepo(tmp_path / field, m))
    assert field in r.stderr, f"單獨刪 {field} 未被擋\n{r.stderr}"


def test_production_tree_all_closed_tickets_are_covered():
    """真樹斷言：目前所有已收案的票都有覆蓋列。

    這條會隨票狀態變化而自然轉紅 —— 那正是它的用途。
    """
    d = json.loads(REG.read_text(encoding="utf-8"))
    tk = d["_schema"]["enforcement_ticket_roles"]["key"]
    tr = d["_schema"]["enforcement_ticket_roles"]
    idi = d[tk]["columns"].index(tr["id"])
    sti = d[tk]["columns"].index(tr["status"])
    closed = d["_schema"]["enforcement_closed_status"]
    enf = d[d["_schema"]["enforcement_keys"][0]]
    ti = enf["columns"].index(d["_schema"]["enforcement_column_roles"]["ticket"])
    covered = {row[ti] for row in enf["rows"]}
    missing = [row[idi] for row in d[tk]["rows"]
               if row[sti] == closed and row[idi] not in covered]
    assert not missing, (
        f"下列票已標收案但未登記產出端覆蓋：{missing}\n"
        "規則：治理票要標收案，其檢查必須擋在產出端；擋不了就具名寫出為什麼。"
    )


def test_mutation_removing_closure_binding_lets_it_through(tmp_path):
    """反面實證：拿掉收案綁定後，未覆蓋的收案票就通過 ⇒ 證明該條非空心。"""
    root = _mkrepo(tmp_path,
                   lambda d: _add_ticket(d, d["_schema"]["enforcement_closed_status"]))
    p = root / "scripts" / GEN.name
    src = p.read_text(encoding="utf-8")
    anchor = '  [ -z "${_fkve_missing}" ] || {'
    assert anchor in src, "mutation 錨點不存在"
    p.write_text(src.replace(anchor, '  [ -n "${_fkve_missing}" ] || {', 1), encoding="utf-8")
    r = _check(root)
    assert "登記產出端覆蓋" not in r.stderr, (
        f"拿掉收案綁定後仍報同一訊息 ⇒ 這條 mutation 是空心的\n{r.stderr}"
    )


def test_note_must_not_mention_nonexistent_fact_key(tmp_path):
    """🔴 檢查 ⑨：`enforcement_note` 不得提及已不存在的 fact-key。

    〔CODEX-R3-P2-01，戳記輪拒簽〕schema 內的散文最容易變成過期副本：
    該 note 一度同時寫著「四道檢查」（實際八道）與 `S0.6` 已刪除的來源 key。
    主委第一次修訂只改了前者，把作廢 key 留在「原文指向 X，已刪除」的歷史括註裡
    ⇒ `jq ... contains("governance-ticket-closure")` 仍 rc=0，codex 據此拒簽。

    判準封閉：note 內任何 `governance-<名>` token 都必須是本註冊表現存的 key。
    """
    def m(d):
        d["_schema"]["enforcement_note"] = (
            d["_schema"].get("enforcement_note", "")
            + "（原文指向 governance-ticket-closure，該來源已刪除）"
        )
    r = _check(_mkrepo(tmp_path, m))
    assert r.returncode != 0, (
        f"note 提及作廢 key 卻放行 ⇒ schema 散文可留過期來源：{r.stdout}{r.stderr}"
    )
    assert "不存在之 fact-key" in r.stderr, f"rc≠0 但未具名 ⇒ 可能紅在別的原因：{r.stderr}"
    assert "governance-ticket-closure" in r.stderr, f"未指出是哪個 key：{r.stderr}"


def test_s62_ticket_without_gap_text_is_rejected(tmp_path):
    """🔴 檢查 ⑩（S6.2）：票之「狀態依據」未寫出還缺什麼 ⇒ fail-closed。

    病根：61 張票原本只有 13 張寫了缺口，其餘只寫「r3 三家一致」——那是**來源**不是**內容**，
    等於狀態單一化了、待辦內容卻還要回去翻已標作廢的 backlog 長文。
    """
    def m(d):
        tr = d["_schema"]["enforcement_ticket_roles"]
        t = d[tr["key"]]
        bi = t["columns"].index(tr["basis"])
        t["rows"][0][bi] = "r3 三家一致"          # 只有來源，沒有內容
    r = _check(_mkrepo(tmp_path, m))
    assert r.returncode != 0, f"票無「還缺什麼」卻放行 ⇒ 待辦內容仍散在作廢檔：{r.stdout}{r.stderr}"
    assert "未寫出還缺什麼" in r.stderr, f"rc≠0 但未具名 ⇒ 可能紅在別的原因：{r.stderr}"


def test_s62_no_residual_marker_is_accepted(tmp_path):
    """對照組：`無殘留` 是合法答案（使用者裁定不做／客觀不可執行者）。

    若不接受，會逼人為了過閘而編造不存在的待辦——那比沒有檢查更糟。
    """
    def m(d):
        tr = d["_schema"]["enforcement_ticket_roles"]
        t = d[tr["key"]]
        bi = t["columns"].index(tr["basis"])
        t["rows"][0][bi] = "使用者裁定不做 ｜無殘留：非積壓工作"
    r = _check(_mkrepo(tmp_path, m))
    assert "未寫出還缺什麼" not in r.stderr, f"`無殘留` 被誤擋 ⇒ 會逼人編造待辦：{r.stderr}"


def test_s62_markers_cannot_be_emptied(tmp_path):
    """🔴 清空 `ticket_basis_markers` ⇒ fail-closed，不得讓 S6.2 閘整段停用。

    〔COMPOSER-R1-P1-02／GROK-R1-P2-01／CODEX-R1-P1-02 三家獨立實構〕
    初版以 `// []` 取值並在長度 0 時整段跳過——刪除、改 null 或清空即可關掉整道閘。
    這與 S1.2「刪掉 settings.json 即跳過對證」是同一型的自關 fail-open，我才剛修過同型。
    """
    def m(d):
        d["_schema"]["ticket_basis_markers"] = []
    r = _check(_mkrepo(tmp_path, m))
    assert r.returncode != 0, f"清空 markers 卻放行 ⇒ S6.2 閘可被靜默停用：{r.stdout}{r.stderr}"
    assert "ticket_basis_markers" in r.stderr, f"rc≠0 但未具名：{r.stderr}"


def test_s62_marker_with_empty_payload_is_rejected(tmp_path):
    """🔴 `｜還缺：` 後面留空 ⇒ fail-closed（marker 在場不等於寫了內容）。

    〔COMPOSER-R1-P1-01／GROK-R1-P2-02／CODEX-R1-P1-03〕
    初版只驗子字串是否存在，於是空殼可過——正好退回 S4.3 之前「有標記無內容」的狀態。
    """
    def m(d):
        tr = d["_schema"]["enforcement_ticket_roles"]
        t = d[tr["key"]]
        bi = t["columns"].index(tr["basis"])
        t["rows"][0][bi] = "r3 三家一致 ｜還缺：   "
    r = _check(_mkrepo(tmp_path, m))
    assert r.returncode != 0, f"空 payload 被放行 ⇒ 檢查⑩仍是形式檢查：{r.stdout}{r.stderr}"
    assert "未寫出還缺什麼" in r.stderr, f"rc≠0 但未具名：{r.stderr}"


def test_s62_deleting_a_ticket_row_is_caught(tmp_path):
    """🔴 刪掉整列票 ⇒ fail-closed（刪列不等於票不存在）。

    〔CODEX-R1-P1-04〕檢查 ⑩ 只遍歷**現存** rows，故刪列後剩餘列全數通過。
    修法＝把 ticket_universe 對帳接進同一個 --check 入口，
    使「每張票都要寫還缺什麼」成為真的閉合不變式，而不是「每張還在表裡的票」。
    """
    def m(d):
        tr = d["_schema"]["enforcement_ticket_roles"]
        d[tr["key"]]["rows"].pop(0)
    r = _check(_mkrepo(tmp_path, m))
    assert r.returncode != 0, f"刪列被放行 ⇒ 少寫一張票只要把它刪掉即可：{r.stdout}{r.stderr}"
    assert "票全集對帳" in r.stderr, f"rc≠0 但未具名對帳失敗 ⇒ 可能紅在別的原因：{r.stderr}"


def test_note_mentioning_live_fact_key_is_allowed(tmp_path):
    """對照組：note 提及**現存**的 fact-key 必須通過，否則會逼人不敢在 note 裡寫來源。"""
    def m(d):
        live = [k for k in d if k != "_schema"][0]
        d["_schema"]["enforcement_note"] = d["_schema"].get("enforcement_note", "") + f"（見 {live}）"
    r = _check(_mkrepo(tmp_path, m))
    assert "不存在之 fact-key" not in r.stderr, (
        f"提及現存 key 被誤擋 ⇒ 檢查 ⑨ 過寬：{r.stderr}"
    )
