"""FKPERF 差分語料（docs/FKPERF_SPEC.md Task 0.1 語料①～⑤、出口清單、stderr 行歸類）。

出口語料（exit 類）逐筆手寫建法；每筆之預期首行為 oracle 實跑所得之字面（`{root}`＝沙箱根目錄，
比對時代換）。`EXIT_CATALOG` 另以字面獨立列出，供 `test_exit_catalog_equals_corpus_labels` 對帳。
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from tests.governance import _fkperf_oracle as fo

REG = fo.REG_REL
Build = Callable[[Path], None]


# ---------------------------------------------------------------- 建法 helper

def _tree(*edits: Build, omit: Sequence[str] = (), git_init: bool = True, minimal: bool = False) -> Build:
    def build(root: Path) -> None:
        fo.build_sandbox_tree(root, omit=omit, git_init=git_init, minimal=minimal)
        for e in edits:
            e(root)
    return build


def _reg(fn: Callable[[dict], None]) -> Build:
    def edit(root: Path) -> None:
        p = root / REG
        data = json.loads(p.read_text(encoding="utf-8"))
        fn(data)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return edit


def _raw_reg(text: str) -> Build:
    def edit(root: Path) -> None:
        (root / REG).write_text(text, encoding="utf-8")
    return edit


def _write(rel: str, text: str) -> Build:
    def edit(root: Path) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return edit


def _symlink(rel: str, target: str) -> Build:
    def edit(root: Path) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target.replace("{root}", str(root)), p)
    return edit


def _sync(root: Path) -> None:
    """合規之註冊表改動後，以 oracle 入口 `--write` 同步宿主區塊（兩沙箱建樹時皆為 oracle 入口）。"""
    r = subprocess.run(["bash", fo.ENTRY_REL, "--write"], cwd=str(root), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _fakebin(dirname: str, drop: Sequence[str]) -> Build:
    """建 `{root}/../<dirname>`：系統常用工具之 symlink，排除 `drop`（C-5 前置例外用）。"""
    tools = ("bash", "sh", "env", "dirname", "basename", "cat", "sed", "awk", "grep", "sort", "tr", "wc", "git",
             "mktemp", "rm", "cp", "mv", "head", "tail", "cut", "uniq", "date", "ls", "mkdir", "jq", "python3")

    def edit(root: Path) -> None:
        d = root.parent / dirname
        d.mkdir(exist_ok=True)
        for tool in tools:
            if tool in drop or (d / tool).exists():
                continue
            real = subprocess.run(["/usr/bin/which", tool], capture_output=True, text=True).stdout.strip()
            if real:
                (d / tool).symlink_to(real)
    return edit


def _x(label: str, first: str, args: Sequence[str], build: Build, rc: int = 1, **kw) -> Tuple[str, fo.Case]:
    return label, fo.Case(f"exit-{label}", tuple(args), build, rc, first, **kw)


def _set(key: str, field: str, value) -> Build:
    def fn(d: dict) -> None:
        d[key][field] = value
    return _reg(fn)


def _schema(field: str, value) -> Build:
    def fn(d: dict) -> None:
        d["_schema"][field] = value
    return _reg(fn)


def _schema_pop(*fields: str) -> Build:
    def fn(d: dict) -> None:
        for f in fields:
            d["_schema"].pop(f)
    return _reg(fn)


def _schema_append(field: str, value) -> Build:
    return _reg(lambda d: d["_schema"][field].append(value))


def _cell(key: str, column: str, value: str, row: int = 0) -> Build:
    def fn(d: dict) -> None:
        d[key]["rows"][row][d[key]["columns"].index(column)] = value
    return _reg(fn)


def _first_row_where(key: str, column: str, pred: Callable[[str], bool]) -> Callable[[dict], int]:
    def find(d: dict) -> int:
        ci = d[key]["columns"].index(column)
        return next(i for i, r in enumerate(d[key]["rows"]) if pred(r[ci]))
    return find


def _cell_where(key: str, column: str, value: str, match_col: str, pred: Callable[[str], bool]) -> Build:
    def fn(d: dict) -> None:
        i = _first_row_where(key, match_col, pred)(d)
        d[key]["rows"][i][d[key]["columns"].index(column)] = value
    return _reg(fn)


def _append_text(rel: str, text: str) -> Build:
    def edit(root: Path) -> None:
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")
    return edit


def _rm(rel: str) -> Build:
    """於 `git add` 之後刪檔（索引仍列該檔 ⇒ 範圍掃描見「非 regular file」）。"""
    return lambda root: (root / rel).unlink()


# ---------------------------------------------------------------- 出口語料（exit 類）

EXIT_CASES: List[Tuple[str, fo.Case]] = [
    # _fk_preflight
    _x("missing_jq", "gen_fact_key_blocks: 缺 jq → fail-closed", ["--check"],
       _tree(_fakebin("bin_nojq", ("jq",)), _fakebin("bin_nopy", ("python3",))),
       oracle_env={"PATH": "{root}/../bin_nojq"}, new_env={"PATH": "{root}/../bin_nopy"}, entry="entry",
       expect_new=(1, "gen_fact_key_blocks: 缺 python3 → fail-closed")),
    _x("registry_missing", "gen_fact_key_blocks: 缺註冊表 {root}/scripts/fact_keys.json → fail-closed", [],
       _tree(omit=(REG,))),
    _x("registry_not_object", "gen_fact_key_blocks: 註冊表 {root}/scripts/fact_keys.json 非合法 JSON 物件 → fail-closed",
       [], _tree(_raw_reg("[1]\n"))),
    # _fk_rows_source_rows（key committee-roster：rows_source → scripts/governance_families.json）
    _x("rows_source_with_rows", "gen_fact_key_blocks: key committee-roster 之 rows_source 與 rows／rows_filter 並存（三者擇一）→ fail-closed", [], _tree(_set("committee-roster", "rows", []))),
    _x("rows_source_shape", "gen_fact_key_blocks: key committee-roster 之 rows_source 形式不符（須恰為 {file: 非空字串, path: 非空字串陣列}）→ fail-closed", [], _tree(_set("committee-roster", "rows_source", {"file": "x.json"}))),
    _x("rows_source_absolute", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 為絕對路徑（/etc/hosts）→ fail-closed", [],
       _tree(_set("committee-roster", "rows_source", {"file": "/etc/hosts", "path": ["a"]}))),
    _x("rows_source_dot_segment", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 含 .／.. 或空路徑段（scripts/../scripts/governance_families.json）→ fail-closed", [],
       _tree(_set("committee-roster", "rows_source", {"file": "scripts/../scripts/governance_families.json",
                                                        "path": ["active_stampers"]}))),
    _x("rows_source_symlink", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 為 symlink（scripts/gf_link.json）→ fail-closed", [],
       _tree(_symlink("scripts/gf_link.json", "governance_families.json"),
             _set("committee-roster", "rows_source", {"file": "scripts/gf_link.json", "path": ["active_stampers"]}))),
    _x("rows_source_missing", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 不存在或非一般檔（scripts/governance_families.json）→ fail-closed", [], _tree(omit=("scripts/governance_families.json",))),
    _x("rows_source_outside_repo", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 實體路徑在 repo 外（scripts/extdir/a.json）→ fail-closed", [],
       _tree(_write("../ext_rs/a.json", '{"a": ["x"]}\n'), _symlink("scripts/extdir", "{root}/../ext_rs"),
             _set("committee-roster", "rows_source", {"file": "scripts/extdir/a.json", "path": ["a"]}))),
    _x("rows_source_not_json", "gen_fact_key_blocks: key committee-roster 之 rows_source.file 非單一合法 JSON 值（scripts/rs_bad.json）→ fail-closed", [],
       _tree(_write("scripts/rs_bad.json", "1 2\n"),
             _set("committee-roster", "rows_source", {"file": "scripts/rs_bad.json", "path": ["a"]}))),
    _x("rows_source_path_absent", "gen_fact_key_blocks: key committee-roster 之 rows_source.path [\"no_such\"] 在 scripts/governance_families.json 中不存在 → fail-closed", [],
       _tree(_set("committee-roster", "rows_source", {"file": "scripts/governance_families.json", "path": ["no_such"]}))),
    _x("rows_source_not_string_array", "gen_fact_key_blocks: key committee-roster 之 rows_source 所指值非字串陣列（scripts/rs_num.json [\"a\"]）→ fail-closed", [],
       _tree(_write("scripts/rs_num.json", '{"a": [1, 2]}\n'),
             _set("committee-roster", "rows_source", {"file": "scripts/rs_num.json", "path": ["a"]}))),
    _x("rows_source_over_999", "gen_fact_key_blocks: key committee-roster 之 rows_source 元素逾 999（三位序號不足以保序）→ fail-closed", [],
       _tree(_write("scripts/rs_big.json", json.dumps({"a": [f"f{i}" for i in range(1000)]}) + "\n"),
             _set("committee-roster", "rows_source", {"file": "scripts/rs_big.json", "path": ["a"]}))),
    # _fk_rows_filter_rows（key handoff-current）
    _x("rows_filter_with_rows", "gen_fact_key_blocks: key handoff-current 之 rows_filter 與 rows／rows_source 並存（三者擇一）→ fail-closed", [], _tree(_set("handoff-current", "rows", []))),
    _x("rows_filter_shape", "gen_fact_key_blocks: key handoff-current 之 rows_filter 形式不符（須恰為 {source_keys, status_column, allow}；陣列非空、元素非空不重複）→ fail-closed", [],
       _tree(_set("handoff-current", "rows_filter", {"source_keys": ["handoff-pending"], "status_column": "狀態"}))),
    _x("rows_filter_enum_absent", "gen_fact_key_blocks: key handoff-current 之 rows_filter.allow 無法對照 _schema.status_enum（缺席或非陣列）→ fail-closed", [], _tree(_reg(lambda d: d["_schema"].pop("status_enum")))),
    _x("rows_filter_allow_outside_enum", "gen_fact_key_blocks: key handoff-current 之 rows_filter.allow 含 status_enum 以外之值：不存在之狀態→ fail-closed", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"]["allow"].append("不存在之狀態")))),
    _x("rows_filter_columns_head", "gen_fact_key_blocks: key handoff-current 用 rows_filter 須宣告 columns 且首欄為『序』、至少一個投影欄（唯一排序點會重排列，序號欄保存來源順序）→ fail-closed", [],
       _tree(_set("handoff-current", "columns", ["識別碼", "序", "狀態", "權威路徑", "下一步"]))),
    _x("rows_filter_self_source", "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key 不得為自身或保留鍵（handoff-current）→ fail-closed", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"]["source_keys"].append("handoff-current")))),
    _x("rows_filter_source_absent", "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key 不存在：no-such-key → fail-closed", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"]["source_keys"].append("no-such-key")))),
    _x("rows_filter_chained", "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key handoff-todo 本身亦為 rows_filter（不支援串接）→ fail-closed", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"]["source_keys"].append("handoff-todo")))),
    _x("rows_filter_source_missing_column", "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key eventscan-rulings 缺欄：下一步 權威路徑 狀態 識別碼 → fail-closed", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"]["source_keys"].append("eventscan-rulings")))),
    _x("rows_filter_source_row_width", "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key handoff-pending 之 rows 缺席或列長與 columns 不符 → fail-closed", [],
       _tree(_reg(lambda d: d["handoff-pending"]["rows"].append(["999", "HP-X"])))),
    _x("rows_filter_seq_overflow", "gen_fact_key_blocks: key handoff-current 之 rows_filter 逾序號位數（來源 key 數限兩位、單一來源列數限三位）→ fail-closed", ["--write"],
       _tree(_reg(lambda d: d["handoff-pending"].__setitem__("rows", [
           [f"{i % 1000:03d}", f"HP-OVF{i:04d}", "進行中", "docs/FKPERF_SPEC.md", f"做 OVF{i}"] for i in range(1000)])))),
    # _fk_validate_keys
    _x("key_name_invalid", "gen_fact_key_blocks: fact-key 名稱不合法（須符 ^[a-z0-9][a-z0-9-]*$）→ fail-closed:", [], _tree(_reg(lambda d: d.__setitem__("Bad_Key", {"target": "HANDOFF.md", "rows": []})))),
    # _fk_targets（key committee-roster 為 keys[] 首位；--write 走 _fk_targets）
    _x("target_array_non_string", "gen_fact_key_blocks: key committee-roster 之 target 陣列含非字串元素 → fail-closed", ["--write"], _tree(_set("committee-roster", "target", ["docs/MULTI_AGENT_ORCHESTRATION.md", 1]))),
    _x("target_type", "gen_fact_key_blocks: key committee-roster 之 target 型別不符（須 string 或 array of string）→ fail-closed", ["--write"], _tree(_set("committee-roster", "target", 5))),
    _x("target_empty", "gen_fact_key_blocks: key committee-roster 缺 target 或 target 為空陣列 → fail-closed", ["--write"], _tree(_set("committee-roster", "target", []))),
    _x("target_duplicate", "gen_fact_key_blocks: key committee-roster 之 target 含重複路徑 → fail-closed", ["--write"],
       _tree(_set("committee-roster", "target", ["docs/MULTI_AGENT_ORCHESTRATION.md", "docs/MULTI_AGENT_ORCHESTRATION.md"]))),
    _x("target_absolute", "gen_fact_key_blocks: key committee-roster 之 target 不得為絕對路徑：/etc/hosts", ["--write"], _tree(_set("committee-roster", "target", "/etc/hosts"))),
    _x("target_dotdot", "gen_fact_key_blocks: key committee-roster 之 target 不得含 ..：docs/../HANDOFF.md", ["--write"], _tree(_set("committee-roster", "target", "docs/../HANDOFF.md"))),
    # _fk_validate_rows
    _x("rows_type_mismatch", "gen_fact_key_blocks: key x 之 rows 型別不符（須為字串陣列之陣列）→ fail-closed", [], _tree(_raw_reg('{"x": NaN}\n'), minimal=True)),
    # _fk_validate_shape（key eventscan-banner）
    _x("render_mode", "gen_fact_key_blocks: key eventscan-banner 之 render='html' 不在 {tsv table} → fail-closed", [], _tree(_set("eventscan-banner", "render", "html"))),
    _x("render_type", "gen_fact_key_blocks: key eventscan-banner 之 render 型別不符（須字串）→ fail-closed", [], _tree(_set("eventscan-banner", "render", 1))),
    _x("table_no_columns", "gen_fact_key_blocks: key eventscan-banner render=table 但未宣告 columns（無表頭）→ fail-closed", [], _tree(_reg(lambda d: d["eventscan-banner"].pop("columns")))),
    _x("columns_invalid", "gen_fact_key_blocks: key eventscan-banner 之 columns 非法（須非空字串陣列；元素非空、不重複、不含 | 或任何控制字元）→ fail-closed", [], _tree(_set("eventscan-banner", "columns", ["序", "位置", "字面", "解除|條件"]))),
    _x("row_width", "gen_fact_key_blocks: key eventscan-banner 有列之欄數與 columns 宣告不符 → fail-closed", [], _tree(_reg(lambda d: d["eventscan-banner"]["rows"].append(["998", "x"])))),
    _x("cell_control_char", "gen_fact_key_blocks: key eventscan-banner 之儲存格含控制字元（破壞逐列語義）→ fail-closed", [], _tree(_reg(lambda d: d["eventscan-banner"]["rows"][0].__setitem__(2, "a\x01b")))),
    _x("cell_pipe_in_table", "gen_fact_key_blocks: key eventscan-banner render=table 之儲存格含 |（會切碎表格）→ fail-closed", [], _tree(_reg(lambda d: d["eventscan-banner"]["rows"][0].__setitem__(2, "a|b")))),
    # _fk_markers_ok／_fk_reject_unregistered_blocks（--check）
    _x("marker_count", "FACTKEY MARKER: committee-roster in docs/MULTI_AGENT_ORCHESTRATION.md（BEGIN=2 END=1，須各恰 1）→ fail-closed", ["--check"],
       _tree(_append_text("docs/MULTI_AGENT_ORCHESTRATION.md", "<!-- BEGIN GENERATED: committee-roster -->\n"))),
    _x("unregistered_block", "FACTKEY UNREGISTERED BLOCK: 'ghost-key' in HANDOFF.md（不在 {root}/scripts/fact_keys.json）→ fail-closed", ["--check"],
       _tree(_append_text("HANDOFF.md", "<!-- BEGIN GENERATED: ghost-key -->\n<!-- END GENERATED: ghost-key -->\n"))),
    # _fk_validate_schema_sets（--write）
    _x("schema_set_invalid", "gen_fact_key_blocks: _schema.status_scope_grandfathered 缺席／非陣列／為空／含非字串 → fail-closed", ["--write"], _tree(_schema_pop("status_scope_grandfathered"))),
    _x("status_keys_unregistered", "gen_fact_key_blocks: _schema.status_keys 含未註冊 key 'no-such-key' → fail-closed", ["--write"], _tree(_schema_append("status_keys", "no-such-key"))),
    _x("status_scope_wildcard", "gen_fact_key_blocks: _schema.status_scope 不得含 wildcard：docs/*.md → fail-closed", ["--write"], _tree(_schema_append("status_scope", "docs/*.md"))),
    # _fk_scope_files／_fk_status_hits_in_lines／_fk_reject_handwritten_status
    _x("scope_not_git_tree", "FACTKEY SCAN: . 非 git 工作樹 ⇒ fail-closed（不得靜默退回只掃 target）", ["--check"], _tree(git_init=False)),
    _x("status_hits_ids_empty", "gen_fact_key_blocks: --status-hits 識別碼集合為空 → fail-closed", ["--status-hits", "lines.txt"],
       _tree(_write("lines.txt", "L1\tx\n"), _reg(lambda d: [d[k].__setitem__("rows", []) for k in
             d["_schema"]["status_keys"] + d["_schema"]["docrot2_status_keys"]])), rc=2),
    _x("scope_symlink", "FACTKEY SCAN: 白話說明/link.md 為 symlink ⇒ fail-closed", ["--check"], _tree(_symlink("白話說明/link.md", "README.md"))),
    _x("scope_not_regular", "FACTKEY SCAN: 白話說明/現在做到哪.md 非 regular file（submodule／缺檔）⇒ fail-closed", ["--check"], _tree(_rm("白話說明/現在做到哪.md"))),
    _x("handwritten_status", "FACTKEY HANDWRITTEN STATUS: 白話說明/hw.md:1 識別碼=WL-01 狀態=收案", ["--check"], _tree(_write("白話說明/hw.md", "WL-01 收案\n"))),
    # _fk_validate_criteria（emit）
    _x("criteria_schema_partial", "gen_fact_key_blocks: _schema 已宣告部分判準欄，但缺 criteria_live_status → fail-closed（判準 schema 為一整組，不得單獨刪）", [], _tree(_schema_pop("criteria_live_status"))),
    _x("criteria_keys_empty", "gen_fact_key_blocks: _schema.criteria_keys 為空 → fail-closed（空清單會使三道判準檢查全部靜默停用）", [], _tree(_schema("criteria_keys", []))),
    _x("criteria_status_enum_invalid", "gen_fact_key_blocks: _schema.criteria_status_enum 非法 → fail-closed", [], _tree(_schema("criteria_status_enum", []))),
    _x("criteria_live_status_empty", "gen_fact_key_blocks: _schema.criteria_live_status 缺席或為空 → fail-closed", [], _tree(_schema("criteria_live_status", ""))),
    _x("criteria_live_status_outside", "gen_fact_key_blocks: criteria_live_status='不存在之狀態' 不在 criteria_status_enum 內 → fail-closed", [], _tree(_schema("criteria_live_status", "不存在之狀態"))),
    _x("criteria_keys_unregistered", "gen_fact_key_blocks: criteria_keys 含未註冊 key 'no-such-key' → fail-closed", [], _tree(_schema_append("criteria_keys", "no-such-key"))),
    _x("criteria_role_missing", "gen_fact_key_blocks: key governance-criteria 缺角色欄（criteria_column_roles 未宣告或 columns 無該欄）: oracle → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["criteria_column_roles"].__setitem__("oracle", "不存在欄")))),
    _x("criteria_status_outside", "gen_fact_key_blocks: key governance-criteria 之狀態值不在 criteria_status_enum 內 → fail-closed:", [], _tree(_cell("governance-criteria", "狀態", "不存在之狀態"))),
    _x("criteria_conflict", "gen_fact_key_blocks: key governance-criteria 有互斥判準（同適用範圍同條件、狀態為現行、期望相異）→ fail-closed:", ["--write"], _tree(_reg(lambda d: d["governance-criteria"]["rows"].append(
        [("C-999" if c == "判準ID" else ("1" if v == "0" else "0") if c == "期望rc" else v)
         for c, v in zip(d["governance-criteria"]["columns"], d["governance-criteria"]["rows"][0])])))),
    # _fk_reject_rc_claims_outside_blocks（--check）
    _x("rc_claim_outside_block", "gen_fact_key_blocks: 判準宿主 docs/GOV_CRITERIA_REGISTRY.md 於生成區塊外陳述期望結束狀態（改寫為判準 ID 指標）→ fail-closed:", ["--check"],
       _tree(_append_text("docs/GOV_CRITERIA_REGISTRY.md", "\n本檢查 rc=0 即通過。\n"))),
    # _fk_validate_mechanism（emit）／_fk_reject_unregistered_mechanisms（--write）
    _x("mechanism_schema_partial", "gen_fact_key_blocks: _schema 已宣告部分機制欄，但缺 mechanism_tokens → fail-closed（機制 schema 為一整組，不得單獨刪）", [], _tree(_schema_pop("mechanism_tokens"))),
    _x("mechanism_schema_array_invalid", "gen_fact_key_blocks: _schema.mechanism_keys 非法（須非空字串陣列）→ fail-closed", [], _tree(_schema("mechanism_keys", []))),
    _x("mechanism_live_status_empty", "gen_fact_key_blocks: _schema.mechanism_live_status 缺席或為空 → fail-closed", [], _tree(_schema("mechanism_live_status", ""))),
    _x("mechanism_live_status_outside", "gen_fact_key_blocks: mechanism_live_status='不存在之狀態' 不在 mechanism_status_enum 內 → fail-closed", [], _tree(_schema("mechanism_live_status", "不存在之狀態"))),
    _x("mechanism_scope_wildcard", "gen_fact_key_blocks: _schema.mechanism_scope 不得含 wildcard：docs/*.md → fail-closed", [], _tree(_schema_append("mechanism_scope", "docs/*.md"))),
    _x("mechanism_scope_prefix", "gen_fact_key_blocks: _schema.mechanism_scope 須為 exact path，不得為目錄前綴：docs/ → fail-closed（opt-in 必須逐檔顯式）", [], _tree(_schema_append("mechanism_scope", "docs/"))),
    _x("mechanism_scope_absolute", "gen_fact_key_blocks: _schema.mechanism_scope 不得為絕對路徑或含 ..：/etc/hosts → fail-closed", [], _tree(_schema_append("mechanism_scope", "/etc/hosts"))),
    _x("mechanism_keys_unregistered", "gen_fact_key_blocks: mechanism_keys 含未註冊 key 'no-such-key' → fail-closed", [], _tree(_schema_append("mechanism_keys", "no-such-key"))),
    _x("mechanism_role_missing", "gen_fact_key_blocks: key governance-mechanism 缺角色欄（mechanism_column_roles 未宣告或 columns 無該欄）: finding → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["mechanism_column_roles"].__setitem__("finding", "不存在欄")))),
    _x("mechanism_status_outside", "gen_fact_key_blocks: key governance-mechanism 之狀態值不在 mechanism_status_enum 內 → fail-closed:", [], _tree(_cell("governance-mechanism", "狀態", "不存在之狀態"))),
    _x("mechanism_token_outside", "gen_fact_key_blocks: key governance-mechanism 之平台機制不在 _schema.mechanism_tokens 封閉表內 → fail-closed:", [], _tree(_cell("governance-mechanism", "平台機制", "bogus-token"))),
    _x("mechanism_id_duplicate", "gen_fact_key_blocks: key governance-mechanism 有重複機制ID → fail-closed:", [],
       _tree(_reg(lambda d: d["governance-mechanism"]["rows"].append(list(d["governance-mechanism"]["rows"][0]))))),
    _x("mechanism_evidence_prefix", "gen_fact_key_blocks: key governance-mechanism 之證據 'note:xyz' 前綴不在 {receipt assumed} → fail-closed", [], _tree(_cell("governance-mechanism", "證據", "note:xyz"))),
    _x("mechanism_evidence_empty", "gen_fact_key_blocks: key governance-mechanism 之證據 'receipt:' 缺冒號後之內容 → fail-closed", [], _tree(_cell("governance-mechanism", "證據", "receipt:"))),
    _x("mechanism_receipt_absolute", "gen_fact_key_blocks: key governance-mechanism 之 receipt 路徑不得為絕對路徑或含 ..：/etc/hosts → fail-closed", [], _tree(_cell("governance-mechanism", "證據", "receipt:/etc/hosts"))),
    _x("mechanism_receipt_symlink", "gen_fact_key_blocks: key governance-mechanism 之 receipt 為 symlink：handoffs/link_receipt.md → fail-closed（可指向 repo 外，證據不可稽核）", [],
       _tree(_symlink("handoffs/link_receipt.md", "reconcile/20260813-govwl03-x-consult-r1/synth.md"),
             _cell("governance-mechanism", "證據", "receipt:handoffs/link_receipt.md"))),
    _x("mechanism_receipt_missing", "gen_fact_key_blocks: key governance-mechanism 之 receipt 指向不存在之檔：handoffs/run_receipts/__fkperf_missing__.json → fail-closed（宣稱實跑但無物可查）", ["--write"],
       _tree(_cell("governance-mechanism", "證據", "receipt:handoffs/run_receipts/__fkperf_missing__.json"))),
    _x("mechanism_scope_host_missing", "gen_fact_key_blocks: mechanism_scope 所列宿主不存在：docs/NO_SUCH_HOST.md → fail-closed（缺檔不得靜默略過）", ["--write"], _tree(_schema_append("mechanism_scope", "docs/NO_SUCH_HOST.md"))),
    _x("mechanism_unregistered_in_optin", "gen_fact_key_blocks: opt-in 宿主 docs/GOV_MECHANISM_REGISTRY.md 之改法子樹使用未登記之平台機制（登記到 governance-mechanism 並附 receipt: 或 assumed:）→ fail-closed:", ["--write"],
       _tree(_append_text("docs/GOV_MECHANISM_REGISTRY.md", "\n- 改法：以 renice 調降優先序\n"))),
    # _fk_validate_ticket_universe（--check）
    _x("ticket_universe_mismatch", "gen_fact_key_blocks: 票全集對帳未過（ticket_universe --check rc=1）→ fail-closed", ["--check"],
       _tree(_append_text("handoffs/20260801-GOV-AMEND-BACKLOG.md", "\n## B-9999 fkperf 探針票\n"))),
    # _fk_validate_enforcement（emit）
    _x("enforcement_schema_absent_with_closed", "gen_fact_key_blocks: 票表存在標為『收案』之列，但 _schema 完全沒有產出端覆蓋宣告 → fail-closed", [],
       _tree(_reg(lambda d: [d["_schema"].pop(k) for k in list(d["_schema"]) if k.startswith("enforcement_")]))),
    _x("enforcement_schema_partial", "gen_fact_key_blocks: _schema 已宣告部分產出端覆蓋欄，但缺 enforcement_side_enum → fail-closed（本 schema 為一整組）", [], _tree(_schema_pop("enforcement_side_enum"))),
    _x("enforcement_closed_status_mismatch", "gen_fact_key_blocks: enforcement_closed_status='結案' 不等於生成器寫死之收案字面 '收案' → fail-closed（改字面即脫鉤，已由委員實構）", [], _tree(_schema("enforcement_closed_status", "結案"))),
    _x("enforcement_closed_not_in_enum", "gen_fact_key_blocks: 收案字面 '收案' 不在 status_enum 內 → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["status_enum"].remove("收案")))),
    _x("enforcement_completed_set_mismatch", "gen_fact_key_blocks: enforcement_completed_statuses=[\"收案\"] 不等於生成器寫死之完成語意集合 [\"已完成\",\"已落地\",\"收案\"] → fail-closed", [], _tree(_schema("enforcement_completed_statuses", ["收案"]))),
    _x("enforcement_completed_not_in_enum", "gen_fact_key_blocks: 完成語意集合中有值不在 status_enum 內 → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["status_enum"].remove("已落地")))),
    _x("enforcement_producer_side_outside", "gen_fact_key_blocks: enforcement_producer_side='不存在之側' 不在 enforcement_side_enum 內 → fail-closed", [], _tree(_schema("enforcement_producer_side", "不存在之側"))),
    _x("enforcement_keys_empty", "gen_fact_key_blocks: _schema.enforcement_keys 為空 → fail-closed（空清單會使四道檢查全部靜默停用）", [], _tree(_schema("enforcement_keys", []))),
    _x("enforcement_keys_unregistered", "gen_fact_key_blocks: enforcement_keys 含未註冊 key 'no-such-key' → fail-closed", [], _tree(_schema_append("enforcement_keys", "no-such-key"))),
    _x("enforcement_role_missing", "gen_fact_key_blocks: key governance-enforcement 缺角色欄（enforcement_column_roles）: waiver → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["enforcement_column_roles"].__setitem__("waiver", "不存在欄")))),
    _x("enforcement_side_outside", "gen_fact_key_blocks: key governance-enforcement 之強制側不在 enforcement_side_enum 內 → fail-closed:", [], _tree(_cell("governance-enforcement", "強制側", "不存在之側"))),
    _x("enforcement_settings_missing", "gen_fact_key_blocks: E-001 之掛載點無法對證——hook 設定之承載目錄存在，但設定檔缺失 → fail-closed", [], _tree(omit=(".claude/settings.json",))),
    _x("enforcement_mount_absent", "gen_fact_key_blocks: E-001 宣告為產出端，但掛載點在 settings.json 內不存在：PostToolUse:Edit,Write:scripts/__no_such_hook__.sh → fail-closed（禁自我宣稱）", [],
       _tree(_cell("governance-enforcement", "掛載點", "PostToolUse:Edit,Write:scripts/__no_such_hook__.sh"))),
    _x("enforcement_waiver_placeholder", "gen_fact_key_blocks: E-002 為豁免但豁免理由為空或佔位符 → fail-closed", [],
       _tree(_cell_where("governance-enforcement", "豁免理由", "—", "強制側", lambda v: v == "豁免"))),
    _x("enforcement_ticket_roles_key", "gen_fact_key_blocks: enforcement_ticket_roles.key 'no-such-key' 未註冊 → fail-closed", [],
       _tree(_reg(lambda d: d["_schema"]["enforcement_ticket_roles"].__setitem__("key", "no-such-key")))),
    _x("enforcement_closed_uncovered", "gen_fact_key_blocks: 下列票已標『收案』但未在 governance-enforcement 登記產出端覆蓋 → fail-closed:", [], _tree(_reg(lambda d: d["governance-ticket-sot"]["rows"].append(
        [{"序": "999", "票": "B-9998", "狀態": "收案", "問題描述": "fkperf 探針", "狀態依據": "無殘留：探針票不涉任何檢查"}[c]
         for c in d["governance-ticket-sot"]["columns"]])))),
    _x("enforcement_kind_invalid", "gen_fact_key_blocks: 下列列之「判定型」不合法或與強制側不一致 → fail-closed:", [], _tree(_cell("governance-enforcement", "判定型", "不存在之型"))),
    _x("enforcement_waiver_style", "gen_fact_key_blocks: 下列列之理由不符 S6.1 体例 → fail-closed:", [],
       _tree(_cell_where("governance-enforcement", "豁免理由", "缺體例標記之理由", "強制側", lambda v: v == "產出端"))),
    _x("enforcement_citation_comment_line", "gen_fact_key_blocks: 下列引用之行號落在註解／空行或檔案不存在 → fail-closed:", ["--write"], _tree(_reg(lambda d: next(
        row.__setitem__(j, cell.split("gen_fact_key_blocks.sh:")[0] + "gen_fact_key_blocks.sh:2")
        for row in d["governance-enforcement"]["rows"] for j, cell in enumerate(row)
        if "gen_fact_key_blocks.sh:" in cell)))),
    _x("enforcement_note_ghost_key", "gen_fact_key_blocks: enforcement_note 提及不存在之 fact-key → fail-closed: governance-ghost-key ", [],
       _tree(_reg(lambda d: d["_schema"].__setitem__("enforcement_note",
                                                     d["_schema"].get("enforcement_note", "") + " governance-ghost-key")))),
    _x("ticket_basis_markers_mismatch", "gen_fact_key_blocks: ticket_basis_markers=[] 不等於生成器寫死之集合 [\"無殘留\",\"還缺：\"] → fail-closed", [], _tree(_schema("ticket_basis_markers", []))),
    _x("ticket_basis_missing", "gen_fact_key_blocks: 下列票之「狀態依據」未寫出還缺什麼 → fail-closed:", [], _tree(_cell("governance-ticket-sot", "狀態依據", "r3 三家一致"))),
    _x("enforcement_allowlist_invalid", "gen_fact_key_blocks: _schema.enforcement_ticket_allowlist 缺席或非字串陣列 → fail-closed", [], _tree(_schema("enforcement_ticket_allowlist", [1]))),
    _x("enforcement_ghost_ticket", "gen_fact_key_blocks: governance-enforcement 之「對應票」欄含**票全集外之值** → fail-closed:", [], _tree(_cell("governance-enforcement", "對應票", "GHOST-TICKET"))),
    # _fk_check（--check）
    _x("missing_target_check", "FACTKEY MISSING TARGET: ffdstar-receipt-schema → ./docs/FFDSTAR_SPEC.md → fail-closed", ["--check"], _tree(omit=("docs/FFDSTAR_SPEC.md",))),
    _x("host_drift", "FACTKEY DRIFT: eventscan-banner in docs/EVENTSCAN_SPEC.md（宿主檔與 {root}/scripts/fact_keys.json 不一致；跑 --write 重生成）", ["--check"], _tree(_cell("eventscan-banner", "字面", "fkperf 探針改字"))),
    # _fk_validate_docrot2_status（emit）
    _x("docrot2_schema_invalid", "gen_fact_key_blocks: _schema.docrot2_status_keys／docrot2_status_values 須兩者並存且為非空不重複字串陣列 → fail-closed", [], _tree(_schema("docrot2_status_values", []))),
    _x("docrot2_values_outside_enum", "gen_fact_key_blocks: _schema.docrot2_status_values 含 status_enum 以外之值：不存在之狀態→ fail-closed", [], _tree(_schema_append("docrot2_status_values", "不存在之狀態"))),
    _x("docrot2_keys_unregistered", "gen_fact_key_blocks: _schema.docrot2_status_keys 含未註冊 key：no-such-key → fail-closed", [], _tree(_schema_append("docrot2_status_keys", "no-such-key"))),
    _x("docrot2_key_in_status_keys", "gen_fact_key_blocks: key governance-worklist 不得同時列於 status_keys 與 docrot2_status_keys → fail-closed", [], _tree(_schema_append("docrot2_status_keys", "governance-worklist"))),
    _x("docrot2_columns_invalid", "gen_fact_key_blocks: key roadmap-status 之 columns 須首欄『序』、第二欄『識別碼』，並含『狀態』『權威路徑』『下一步』→ fail-closed", [],
       _tree(_reg(lambda d: d["roadmap-status"]["columns"].__setitem__(-1, "下步")))),
    _x("docrot2_row_violation", "gen_fact_key_blocks: key handoff-pending 之列違規 → fail-closed:", [], _tree(_cell("handoff-pending", "下一步", ""))),
    _x("status_id_duplicate", "gen_fact_key_blocks: status_keys 與 docrot2_status_keys 之識別碼跨 key 重複：HP-PLAINDOCS→ fail-closed", ["--write"], _tree(_reg(lambda d: d["roadmap-status"]["rows"].append(
        ["996", d["handoff-pending"]["rows"][0][1]] + list(d["roadmap-status"]["rows"][0][2:]))))),
    # _fk_validate_handoff_projection（emit）
    _x("handoff_projection_mismatch", "gen_fact_key_blocks: 交接投影與活文件登記不符 → fail-closed:", [],
       _tree(_reg(lambda d: d["handoff-current"]["rows_filter"].__setitem__("allow", ["進行中"])))),
    # _fk_write（--write）與 CLI 參數
    _x("missing_target_write", "FACTKEY MISSING TARGET: ffdstar-receipt-schema → ./docs/FFDSTAR_SPEC.md → fail-closed", ["--write"], _tree(omit=("docs/FFDSTAR_SPEC.md",))),
    _x("status_hits_bad_args", "gen_fact_key_blocks: --status-hits 需恰一個存在之行檔 → fail-closed", ["--status-hits", "no_such_lines.txt"], _tree(), rc=2),
    _x("status_hits_no_docrot2_keys", "gen_fact_key_blocks: --status-hits 需 _schema.docrot2_status_keys 為非空陣列 → fail-closed", ["--status-hits", "lines.txt"],
       _tree(_write("lines.txt", "L1\tx\n"), _schema_pop("docrot2_status_keys")), rc=2),
    _x("too_many_args", "gen_fact_key_blocks: 只接受 0 或 1 個參數（收到 2）→ fail-closed", ["--check", "--write"], _tree(), rc=2),
    _x("unknown_arg", "gen_fact_key_blocks: 未知參數 '--bogus'（可用：--check｜--write｜--help）→ fail-closed", ["--bogus"], _tree(), rc=2),
]

# 出口標籤 → oracle stderr 首行（`{root}`＝沙箱實體路徑）。與 EXIT_CASES 各筆之字面獨立列出以供對帳。
EXIT_CATALOG: Dict[str, str] = {
    "cell_control_char": "gen_fact_key_blocks: key eventscan-banner 之儲存格含控制字元（破壞逐列語義）→ fail-closed",
    "cell_pipe_in_table": "gen_fact_key_blocks: key eventscan-banner render=table 之儲存格含 |（會切碎表格）→ fail-closed",
    "columns_invalid": "gen_fact_key_blocks: key eventscan-banner 之 columns 非法（須非空字串陣列；元素非空、不重複、不含 | 或任何控制字元）→ fail-closed",
    "criteria_conflict": "gen_fact_key_blocks: key governance-criteria 有互斥判準（同適用範圍同條件、狀態為現行、期望相異）→ fail-closed:",
    "criteria_keys_empty": "gen_fact_key_blocks: _schema.criteria_keys 為空 → fail-closed（空清單會使三道判準檢查全部靜默停用）",
    "criteria_keys_unregistered": "gen_fact_key_blocks: criteria_keys 含未註冊 key 'no-such-key' → fail-closed",
    "criteria_live_status_empty": "gen_fact_key_blocks: _schema.criteria_live_status 缺席或為空 → fail-closed",
    "criteria_live_status_outside": "gen_fact_key_blocks: criteria_live_status='不存在之狀態' 不在 criteria_status_enum 內 → fail-closed",
    "criteria_role_missing": "gen_fact_key_blocks: key governance-criteria 缺角色欄（criteria_column_roles 未宣告或 columns 無該欄）: oracle → fail-closed",
    "criteria_schema_partial": "gen_fact_key_blocks: _schema 已宣告部分判準欄，但缺 criteria_live_status → fail-closed（判準 schema 為一整組，不得單獨刪）",
    "criteria_status_enum_invalid": "gen_fact_key_blocks: _schema.criteria_status_enum 非法 → fail-closed",
    "criteria_status_outside": "gen_fact_key_blocks: key governance-criteria 之狀態值不在 criteria_status_enum 內 → fail-closed:",
    "docrot2_columns_invalid": "gen_fact_key_blocks: key roadmap-status 之 columns 須首欄『序』、第二欄『識別碼』，並含『狀態』『權威路徑』『下一步』→ fail-closed",
    "docrot2_key_in_status_keys": "gen_fact_key_blocks: key governance-worklist 不得同時列於 status_keys 與 docrot2_status_keys → fail-closed",
    "docrot2_keys_unregistered": "gen_fact_key_blocks: _schema.docrot2_status_keys 含未註冊 key：no-such-key → fail-closed",
    "docrot2_row_violation": "gen_fact_key_blocks: key handoff-pending 之列違規 → fail-closed:",
    "docrot2_schema_invalid": "gen_fact_key_blocks: _schema.docrot2_status_keys／docrot2_status_values 須兩者並存且為非空不重複字串陣列 → fail-closed",
    "docrot2_values_outside_enum": "gen_fact_key_blocks: _schema.docrot2_status_values 含 status_enum 以外之值：不存在之狀態→ fail-closed",
    "enforcement_allowlist_invalid": "gen_fact_key_blocks: _schema.enforcement_ticket_allowlist 缺席或非字串陣列 → fail-closed",
    "enforcement_citation_comment_line": "gen_fact_key_blocks: 下列引用之行號落在註解／空行或檔案不存在 → fail-closed:",
    "enforcement_closed_not_in_enum": "gen_fact_key_blocks: 收案字面 '收案' 不在 status_enum 內 → fail-closed",
    "enforcement_closed_status_mismatch": "gen_fact_key_blocks: enforcement_closed_status='結案' 不等於生成器寫死之收案字面 '收案' → fail-closed（改字面即脫鉤，已由委員實構）",
    "enforcement_closed_uncovered": "gen_fact_key_blocks: 下列票已標『收案』但未在 governance-enforcement 登記產出端覆蓋 → fail-closed:",
    "enforcement_completed_not_in_enum": "gen_fact_key_blocks: 完成語意集合中有值不在 status_enum 內 → fail-closed",
    "enforcement_completed_set_mismatch": "gen_fact_key_blocks: enforcement_completed_statuses=[\"收案\"] 不等於生成器寫死之完成語意集合 [\"已完成\",\"已落地\",\"收案\"] → fail-closed",
    "enforcement_ghost_ticket": "gen_fact_key_blocks: governance-enforcement 之「對應票」欄含**票全集外之值** → fail-closed:",
    "enforcement_keys_empty": "gen_fact_key_blocks: _schema.enforcement_keys 為空 → fail-closed（空清單會使四道檢查全部靜默停用）",
    "enforcement_keys_unregistered": "gen_fact_key_blocks: enforcement_keys 含未註冊 key 'no-such-key' → fail-closed",
    "enforcement_kind_invalid": "gen_fact_key_blocks: 下列列之「判定型」不合法或與強制側不一致 → fail-closed:",
    "enforcement_mount_absent": "gen_fact_key_blocks: E-001 宣告為產出端，但掛載點在 settings.json 內不存在：PostToolUse:Edit,Write:scripts/__no_such_hook__.sh → fail-closed（禁自我宣稱）",
    "enforcement_note_ghost_key": "gen_fact_key_blocks: enforcement_note 提及不存在之 fact-key → fail-closed: governance-ghost-key ",
    "enforcement_producer_side_outside": "gen_fact_key_blocks: enforcement_producer_side='不存在之側' 不在 enforcement_side_enum 內 → fail-closed",
    "enforcement_role_missing": "gen_fact_key_blocks: key governance-enforcement 缺角色欄（enforcement_column_roles）: waiver → fail-closed",
    "enforcement_schema_absent_with_closed": "gen_fact_key_blocks: 票表存在標為『收案』之列，但 _schema 完全沒有產出端覆蓋宣告 → fail-closed",
    "enforcement_schema_partial": "gen_fact_key_blocks: _schema 已宣告部分產出端覆蓋欄，但缺 enforcement_side_enum → fail-closed（本 schema 為一整組）",
    "enforcement_settings_missing": "gen_fact_key_blocks: E-001 之掛載點無法對證——hook 設定之承載目錄存在，但設定檔缺失 → fail-closed",
    "enforcement_side_outside": "gen_fact_key_blocks: key governance-enforcement 之強制側不在 enforcement_side_enum 內 → fail-closed:",
    "enforcement_ticket_roles_key": "gen_fact_key_blocks: enforcement_ticket_roles.key 'no-such-key' 未註冊 → fail-closed",
    "enforcement_waiver_placeholder": "gen_fact_key_blocks: E-002 為豁免但豁免理由為空或佔位符 → fail-closed",
    "enforcement_waiver_style": "gen_fact_key_blocks: 下列列之理由不符 S6.1 体例 → fail-closed:",
    "handoff_projection_mismatch": "gen_fact_key_blocks: 交接投影與活文件登記不符 → fail-closed:",
    "handwritten_status": "FACTKEY HANDWRITTEN STATUS: 白話說明/hw.md:1 識別碼=WL-01 狀態=收案",
    "host_drift": "FACTKEY DRIFT: eventscan-banner in docs/EVENTSCAN_SPEC.md（宿主檔與 {root}/scripts/fact_keys.json 不一致；跑 --write 重生成）",
    "key_name_invalid": "gen_fact_key_blocks: fact-key 名稱不合法（須符 ^[a-z0-9][a-z0-9-]*$）→ fail-closed:",
    "marker_count": "FACTKEY MARKER: committee-roster in docs/MULTI_AGENT_ORCHESTRATION.md（BEGIN=2 END=1，須各恰 1）→ fail-closed",
    "mechanism_evidence_empty": "gen_fact_key_blocks: key governance-mechanism 之證據 'receipt:' 缺冒號後之內容 → fail-closed",
    "mechanism_evidence_prefix": "gen_fact_key_blocks: key governance-mechanism 之證據 'note:xyz' 前綴不在 {receipt assumed} → fail-closed",
    "mechanism_id_duplicate": "gen_fact_key_blocks: key governance-mechanism 有重複機制ID → fail-closed:",
    "mechanism_keys_unregistered": "gen_fact_key_blocks: mechanism_keys 含未註冊 key 'no-such-key' → fail-closed",
    "mechanism_live_status_empty": "gen_fact_key_blocks: _schema.mechanism_live_status 缺席或為空 → fail-closed",
    "mechanism_live_status_outside": "gen_fact_key_blocks: mechanism_live_status='不存在之狀態' 不在 mechanism_status_enum 內 → fail-closed",
    "mechanism_receipt_absolute": "gen_fact_key_blocks: key governance-mechanism 之 receipt 路徑不得為絕對路徑或含 ..：/etc/hosts → fail-closed",
    "mechanism_receipt_missing": "gen_fact_key_blocks: key governance-mechanism 之 receipt 指向不存在之檔：handoffs/run_receipts/__fkperf_missing__.json → fail-closed（宣稱實跑但無物可查）",
    "mechanism_receipt_symlink": "gen_fact_key_blocks: key governance-mechanism 之 receipt 為 symlink：handoffs/link_receipt.md → fail-closed（可指向 repo 外，證據不可稽核）",
    "mechanism_role_missing": "gen_fact_key_blocks: key governance-mechanism 缺角色欄（mechanism_column_roles 未宣告或 columns 無該欄）: finding → fail-closed",
    "mechanism_schema_array_invalid": "gen_fact_key_blocks: _schema.mechanism_keys 非法（須非空字串陣列）→ fail-closed",
    "mechanism_schema_partial": "gen_fact_key_blocks: _schema 已宣告部分機制欄，但缺 mechanism_tokens → fail-closed（機制 schema 為一整組，不得單獨刪）",
    "mechanism_scope_absolute": "gen_fact_key_blocks: _schema.mechanism_scope 不得為絕對路徑或含 ..：/etc/hosts → fail-closed",
    "mechanism_scope_host_missing": "gen_fact_key_blocks: mechanism_scope 所列宿主不存在：docs/NO_SUCH_HOST.md → fail-closed（缺檔不得靜默略過）",
    "mechanism_scope_prefix": "gen_fact_key_blocks: _schema.mechanism_scope 須為 exact path，不得為目錄前綴：docs/ → fail-closed（opt-in 必須逐檔顯式）",
    "mechanism_scope_wildcard": "gen_fact_key_blocks: _schema.mechanism_scope 不得含 wildcard：docs/*.md → fail-closed",
    "mechanism_status_outside": "gen_fact_key_blocks: key governance-mechanism 之狀態值不在 mechanism_status_enum 內 → fail-closed:",
    "mechanism_token_outside": "gen_fact_key_blocks: key governance-mechanism 之平台機制不在 _schema.mechanism_tokens 封閉表內 → fail-closed:",
    "mechanism_unregistered_in_optin": "gen_fact_key_blocks: opt-in 宿主 docs/GOV_MECHANISM_REGISTRY.md 之改法子樹使用未登記之平台機制（登記到 governance-mechanism 並附 receipt: 或 assumed:）→ fail-closed:",
    "missing_jq": "gen_fact_key_blocks: 缺 jq → fail-closed",
    "missing_target_check": "FACTKEY MISSING TARGET: ffdstar-receipt-schema → ./docs/FFDSTAR_SPEC.md → fail-closed",
    "missing_target_write": "FACTKEY MISSING TARGET: ffdstar-receipt-schema → ./docs/FFDSTAR_SPEC.md → fail-closed",
    "rc_claim_outside_block": "gen_fact_key_blocks: 判準宿主 docs/GOV_CRITERIA_REGISTRY.md 於生成區塊外陳述期望結束狀態（改寫為判準 ID 指標）→ fail-closed:",
    "registry_missing": "gen_fact_key_blocks: 缺註冊表 {root}/scripts/fact_keys.json → fail-closed",
    "registry_not_object": "gen_fact_key_blocks: 註冊表 {root}/scripts/fact_keys.json 非合法 JSON 物件 → fail-closed",
    "render_mode": "gen_fact_key_blocks: key eventscan-banner 之 render='html' 不在 {tsv table} → fail-closed",
    "render_type": "gen_fact_key_blocks: key eventscan-banner 之 render 型別不符（須字串）→ fail-closed",
    "row_width": "gen_fact_key_blocks: key eventscan-banner 有列之欄數與 columns 宣告不符 → fail-closed",
    "rows_filter_allow_outside_enum": "gen_fact_key_blocks: key handoff-current 之 rows_filter.allow 含 status_enum 以外之值：不存在之狀態→ fail-closed",
    "rows_filter_chained": "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key handoff-todo 本身亦為 rows_filter（不支援串接）→ fail-closed",
    "rows_filter_columns_head": "gen_fact_key_blocks: key handoff-current 用 rows_filter 須宣告 columns 且首欄為『序』、至少一個投影欄（唯一排序點會重排列，序號欄保存來源順序）→ fail-closed",
    "rows_filter_enum_absent": "gen_fact_key_blocks: key handoff-current 之 rows_filter.allow 無法對照 _schema.status_enum（缺席或非陣列）→ fail-closed",
    "rows_filter_self_source": "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key 不得為自身或保留鍵（handoff-current）→ fail-closed",
    "rows_filter_seq_overflow": "gen_fact_key_blocks: key handoff-current 之 rows_filter 逾序號位數（來源 key 數限兩位、單一來源列數限三位）→ fail-closed",
    "rows_filter_shape": "gen_fact_key_blocks: key handoff-current 之 rows_filter 形式不符（須恰為 {source_keys, status_column, allow}；陣列非空、元素非空不重複）→ fail-closed",
    "rows_filter_source_absent": "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key 不存在：no-such-key → fail-closed",
    "rows_filter_source_missing_column": "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key eventscan-rulings 缺欄：下一步 權威路徑 狀態 識別碼 → fail-closed",
    "rows_filter_source_row_width": "gen_fact_key_blocks: key handoff-current 之 rows_filter 來源 key handoff-pending 之 rows 缺席或列長與 columns 不符 → fail-closed",
    "rows_filter_with_rows": "gen_fact_key_blocks: key handoff-current 之 rows_filter 與 rows／rows_source 並存（三者擇一）→ fail-closed",
    "rows_source_absolute": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 為絕對路徑（/etc/hosts）→ fail-closed",
    "rows_source_dot_segment": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 含 .／.. 或空路徑段（scripts/../scripts/governance_families.json）→ fail-closed",
    "rows_source_missing": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 不存在或非一般檔（scripts/governance_families.json）→ fail-closed",
    "rows_source_not_json": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 非單一合法 JSON 值（scripts/rs_bad.json）→ fail-closed",
    "rows_source_not_string_array": "gen_fact_key_blocks: key committee-roster 之 rows_source 所指值非字串陣列（scripts/rs_num.json [\"a\"]）→ fail-closed",
    "rows_source_outside_repo": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 實體路徑在 repo 外（scripts/extdir/a.json）→ fail-closed",
    "rows_source_over_999": "gen_fact_key_blocks: key committee-roster 之 rows_source 元素逾 999（三位序號不足以保序）→ fail-closed",
    "rows_source_path_absent": "gen_fact_key_blocks: key committee-roster 之 rows_source.path [\"no_such\"] 在 scripts/governance_families.json 中不存在 → fail-closed",
    "rows_source_shape": "gen_fact_key_blocks: key committee-roster 之 rows_source 形式不符（須恰為 {file: 非空字串, path: 非空字串陣列}）→ fail-closed",
    "rows_source_symlink": "gen_fact_key_blocks: key committee-roster 之 rows_source.file 為 symlink（scripts/gf_link.json）→ fail-closed",
    "rows_source_with_rows": "gen_fact_key_blocks: key committee-roster 之 rows_source 與 rows／rows_filter 並存（三者擇一）→ fail-closed",
    "rows_type_mismatch": "gen_fact_key_blocks: key x 之 rows 型別不符（須為字串陣列之陣列）→ fail-closed",
    "schema_set_invalid": "gen_fact_key_blocks: _schema.status_scope_grandfathered 缺席／非陣列／為空／含非字串 → fail-closed",
    "scope_not_git_tree": "FACTKEY SCAN: . 非 git 工作樹 ⇒ fail-closed（不得靜默退回只掃 target）",
    "scope_not_regular": "FACTKEY SCAN: 白話說明/現在做到哪.md 非 regular file（submodule／缺檔）⇒ fail-closed",
    "scope_symlink": "FACTKEY SCAN: 白話說明/link.md 為 symlink ⇒ fail-closed",
    "status_hits_bad_args": "gen_fact_key_blocks: --status-hits 需恰一個存在之行檔 → fail-closed",
    "status_hits_ids_empty": "gen_fact_key_blocks: --status-hits 識別碼集合為空 → fail-closed",
    "status_hits_no_docrot2_keys": "gen_fact_key_blocks: --status-hits 需 _schema.docrot2_status_keys 為非空陣列 → fail-closed",
    "status_id_duplicate": "gen_fact_key_blocks: status_keys 與 docrot2_status_keys 之識別碼跨 key 重複：HP-PLAINDOCS→ fail-closed",
    "status_keys_unregistered": "gen_fact_key_blocks: _schema.status_keys 含未註冊 key 'no-such-key' → fail-closed",
    "status_scope_wildcard": "gen_fact_key_blocks: _schema.status_scope 不得含 wildcard：docs/*.md → fail-closed",
    "table_no_columns": "gen_fact_key_blocks: key eventscan-banner render=table 但未宣告 columns（無表頭）→ fail-closed",
    "target_absolute": "gen_fact_key_blocks: key committee-roster 之 target 不得為絕對路徑：/etc/hosts",
    "target_array_non_string": "gen_fact_key_blocks: key committee-roster 之 target 陣列含非字串元素 → fail-closed",
    "target_dotdot": "gen_fact_key_blocks: key committee-roster 之 target 不得含 ..：docs/../HANDOFF.md",
    "target_duplicate": "gen_fact_key_blocks: key committee-roster 之 target 含重複路徑 → fail-closed",
    "target_empty": "gen_fact_key_blocks: key committee-roster 缺 target 或 target 為空陣列 → fail-closed",
    "target_type": "gen_fact_key_blocks: key committee-roster 之 target 型別不符（須 string 或 array of string）→ fail-closed",
    "ticket_basis_markers_mismatch": "gen_fact_key_blocks: ticket_basis_markers=[] 不等於生成器寫死之集合 [\"無殘留\",\"還缺：\"] → fail-closed",
    "ticket_basis_missing": "gen_fact_key_blocks: 下列票之「狀態依據」未寫出還缺什麼 → fail-closed:",
    "ticket_universe_mismatch": "gen_fact_key_blocks: 票全集對帳未過（ticket_universe --check rc=1）→ fail-closed",
    "too_many_args": "gen_fact_key_blocks: 只接受 0 或 1 個參數（收到 2）→ fail-closed",
    "unknown_arg": "gen_fact_key_blocks: 未知參數 '--bogus'（可用：--check｜--write｜--help）→ fail-closed",
    "unregistered_block": "FACTKEY UNREGISTERED BLOCK: 'ghost-key' in HANDOFF.md（不在 {root}/scripts/fact_keys.json）→ fail-closed",
}
# oracle（4bdc2d562543）每條寫 stderr 之行 → 歸類（逐行；須合 test_fkperf_differential._site_rules）。
EXIT_SITES: Dict[int, str] = {
    40: "helper",
    44: "missing_jq",
    46: "registry_missing",
    48: "registry_not_object",
    75: "rows_source_with_rows",
    83: "rows_source_shape",
    87: "rows_source_absolute",
    92: "rows_source_dot_segment",
    97: "rows_source_symlink",
    100: "rows_source_missing",
    105: "rows_source_outside_repo",
    109: "rows_source_not_json",
    117: "rows_source_path_absent",
    120: "rows_source_not_string_array",
    123: "rows_source_over_999",
    131: "rows_filter_with_rows",
    141: "rows_filter_shape",
    148: "rows_filter_enum_absent",
    151: "rows_filter_allow_outside_enum",
    155: "rows_filter_columns_head",
    162: "rows_filter_self_source",
    166: "rows_filter_source_absent",
    169: "rows_filter_chained",
    177: "rows_filter_source_missing_column",
    184: "rows_filter_source_row_width",
    193: "rows_filter_seq_overflow",
    213: "tool_failure",
    216: "tool_failure",
    218: "tool_failure",
    221: "tool_failure",
    234: "tool_failure",
    256: "tool_failure",
    276: "key_name_invalid",
    305: "target_array_non_string",
    309: "target_type",
    313: "target_empty",
    318: "target_duplicate",
    324: "target_absolute",
    325: "target_dotdot",
    338: "rows_type_mismatch",
    405: "render_mode",
    407: "render_type",
    409: "table_no_columns",
    411: "columns_invalid",
    413: "row_width",
    415: "cell_control_char",
    417: "cell_pipe_in_table",
    419: "tool_failure",
    463: "marker_count",
    500: "unregistered_block",
    526: "schema_set_invalid",
    534: "status_keys_unregistered",
    544: "status_scope_wildcard",
    590: "scope_not_git_tree",
    691: "tool_failure",
    693: "status_hits_ids_empty",
    695: "tool_failure",
    706: "tool_failure",
    724: "scope_symlink",
    727: "scope_not_regular",
    791: "handwritten_status",
    792: "continuation",
    856: "criteria_schema_partial",
    862: "criteria_keys_empty",
    867: "criteria_status_enum_invalid",
    873: "criteria_live_status_empty",
    877: "criteria_live_status_outside",
    883: "criteria_keys_unregistered",
    891: "criteria_role_missing",
    903: "criteria_status_outside",
    904: "continuation",
    919: "criteria_conflict",
    920: "continuation",
    966: "rc_claim_outside_block",
    967: "continuation",
    1061: "mechanism_schema_partial",
    1070: "mechanism_schema_array_invalid",
    1077: "mechanism_live_status_empty",
    1081: "mechanism_live_status_outside",
    1089: "mechanism_scope_wildcard",
    1092: "mechanism_scope_prefix",
    1095: "mechanism_scope_absolute",
    1106: "mechanism_keys_unregistered",
    1114: "mechanism_role_missing",
    1127: "mechanism_status_outside",
    1128: "continuation",
    1137: "mechanism_token_outside",
    1138: "continuation",
    1146: "mechanism_id_duplicate",
    1147: "continuation",
    1156: "mechanism_evidence_prefix",
    1160: "mechanism_evidence_empty",
    1165: "mechanism_receipt_absolute",
    1172: "mechanism_receipt_symlink",
    1176: "mechanism_receipt_missing",
    1198: "mechanism_scope_host_missing",
    1256: "mechanism_unregistered_in_optin",
    1257: "continuation",
    1402: "ticket_universe_mismatch",
    1403: "continuation",
    1404: "continuation",
    1414: "enforcement_schema_absent_with_closed",
    1415: "continuation",
    1423: "enforcement_schema_partial",
    1431: "enforcement_closed_status_mismatch",
    1435: "enforcement_closed_not_in_enum",
    1440: "tool_failure",
    1442: "enforcement_completed_set_mismatch",
    1443: "continuation",
    1447: "enforcement_completed_not_in_enum",
    1453: "enforcement_producer_side_outside",
    1458: "enforcement_keys_empty",
    1465: "enforcement_keys_unregistered",
    1473: "enforcement_role_missing",
    1486: "enforcement_side_outside",
    1487: "continuation",
    1496: "tool_failure",
    1505: "warning",
    1507: "enforcement_settings_missing",
    1508: "continuation",
    1509: "continuation",
    1511: "enforcement_mount_absent",
    1520: "enforcement_waiver_placeholder",
    1533: "enforcement_ticket_roles_key",
    1553: "tool_failure",
    1556: "enforcement_closed_uncovered",
    1557: "continuation",
    1558: "continuation",
    1559: "continuation",
    1587: "tool_failure",
    1589: "enforcement_kind_invalid",
    1590: "continuation",
    1591: "continuation",
    1592: "continuation",
    1626: "tool_failure",
    1688: "enforcement_waiver_style",
    1689: "continuation",
    1690: "continuation",
    1691: "continuation",
    1692: "continuation",
    1695: "enforcement_citation_comment_line",
    1696: "continuation",
    1697: "continuation",
    1706: "tool_failure",
    1713: "enforcement_note_ghost_key",
    1714: "continuation",
    1715: "continuation",
    1730: "tool_failure",
    1733: "ticket_basis_markers_mismatch",
    1734: "continuation",
    1754: "tool_failure",
    1756: "ticket_basis_missing",
    1757: "continuation",
    1758: "continuation",
    1759: "continuation",
    1786: "warning",
    1787: "continuation",
    1788: "continuation",
    1789: "continuation",
    1796: "enforcement_allowlist_invalid",
    1816: "tool_failure",
    1819: "enforcement_ghost_ticket",
    1820: "continuation",
    1821: "continuation",
    1822: "continuation",
    1842: "tool_failure",
    1848: "missing_target_check",
    1854: "host_drift",
    1897: "docrot2_schema_invalid",
    1904: "docrot2_values_outside_enum",
    1912: "docrot2_keys_unregistered",
    1916: "docrot2_key_in_status_keys",
    1923: "docrot2_columns_invalid",
    1937: "tool_failure",
    1940: "docrot2_row_violation",
    1941: "continuation",
    1954: "tool_failure",
    1956: "status_id_duplicate",
    1983: "tool_failure",
    1985: "handoff_projection_mismatch",
    1986: "continuation",
    2014: "missing_target_write",
    2035: "tool_failure",
    2053: "status_hits_bad_args",
    2059: "status_hits_no_docrot2_keys",
    2066: "too_many_args",
    2083: "unknown_arg",
}
# ---------------------------------------------------------------- 語料①②④⑤

def _ok(case_id: str, first: str, args: Sequence[str], build: Build, **kw) -> fo.Case:
    return fo.Case(case_id, tuple(args), build, 0, first, **kw)


_MIN_SCHEMA = {"status_enum": ["✅"], "status_keys": [], "status_scope": ["docs/"],
               "status_scope_grandfathered": ["docs/__none__.md"]}


def _small(registry: dict, hosts: Sequence[str] = (), *, git_init: bool = True, sync: bool = False) -> Build:
    """比照 test_govb1_factkey_gen._sandbox／_mkroot 與 test_docrot2_registry._fk_sandbox：只含入口、自訂註冊表、
    宿主（各含該 key 之空生成區塊）；`sync`＝以 oracle `--write` 物化區塊內容。"""
    facts = [k for k in registry if k != "_schema"]
    if facts and "_schema" in registry and not registry["_schema"].get("status_keys"):
        registry = {**registry, "_schema": {**registry["_schema"], "status_keys": facts}}  # 同 _sandbox 之注入

    def build(root: Path) -> None:
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / fo.ENTRY_REL).write_bytes(fo._oracle_blob(fo.ENTRY_REL))
        (root / REG).write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        blocks: Dict[str, List[str]] = {}
        for k, v in registry.items():
            if k == "_schema":
                continue
            for t in (v["target"] if isinstance(v["target"], list) else [v["target"]]):
                blocks.setdefault(t, []).append(k)
        for rel in set(hosts) | set(blocks):
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# host\n\n" + "".join(f"<!-- BEGIN GENERATED: {k} -->\n<!-- END GENERATED: {k} -->\n"
                                                 for k in blocks.get(rel, [])), encoding="utf-8")
        if git_init:
            subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
        if sync:
            _sync(root)
    return build


_TSV = {"_schema": _MIN_SCHEMA, "k": {"target": "docs/k.md", "rows": [["030", "c"], ["010", "a"], ["020", "b"]]}}
_TABLE = {"_schema": _MIN_SCHEMA,
          "t": {"target": "docs/t.md", "render": "table", "columns": ["序", "名"], "rows": [["002", "乙"], ["001", "甲"]]}}
_MULTI = {"_schema": _MIN_SCHEMA,
          "m": {"target": ["docs/m1.md", "docs/m2.md"], "rows": [["001", "x"]]}}
_RS = {"_schema": {**_MIN_SCHEMA, "status_keys": []},
       "fam": {"target": "docs/fam.md", "render": "table", "columns": ["序", "家族"],
               "rows_source": {"file": "scripts/src.json", "path": ["active"]}}}


def _real() -> List[fo.Case]:
    lines = "L1\tWL-01 收案\nL2\tHP-X 進行中\n"
    return [
        _ok("real-emit", "<!-- BEGIN GENERATED: committee-roster -->", [], _tree()),
        _ok("real-check", "", ["--check"], _tree()),
        _ok("real-write", "FACTKEY WROTE: committee-roster → docs/MULTI_AGENT_ORCHESTRATION.md", ["--write"], _tree(), watch_files=("docs/EVENTSCAN_SPEC.md", "HANDOFF.md")),
        _ok("real-status-hits", "L1\tWL-01\t收案", ["--status-hits", "lines.txt"], _tree(_write("lines.txt", lines))),
        _ok("help-entry", "# gen_fact_key_blocks.sh — 票 B-25 事實單一來源：生成器 ＋ 漂移檢查（Task 2.1）", ["--help"], _tree(), entry="entry"),
        _ok("help-relative", "# gen_fact_key_blocks.sh — 票 B-25 事實單一來源：生成器 ＋ 漂移檢查（Task 2.1）", ["-h"], _tree(), entry="entry", cwd="scripts", invoke="gen_fact_key_blocks.sh"),
        _ok("help-symlink", "# gen_fact_key_blocks.sh — 票 B-25 事實單一來源：生成器 ＋ 漂移檢查（Task 2.1）", ["--help"], _tree(_symlink("scripts/fk_link.sh", "gen_fact_key_blocks.sh")),
            entry="entry", invoke="scripts/fk_link.sh"),
        fo.Case("real-bad-arg", ("--nope",), _tree(), 2, "gen_fact_key_blocks: 未知參數 '--nope'（可用：--check｜--write｜--help）→ fail-closed"),
        dataclasses.replace(dict(EXIT_CASES)["missing_jq"], case_id="preflight-missing-interpreter"),
    ]


def _sandbox() -> List[fo.Case]:
    src = _write("scripts/src.json", json.dumps({"active": ["codex", "composer", "grok"]}) + "\n")
    return [
        _ok("sb-tsv-emit", "<!-- BEGIN GENERATED: k -->", [], _small(_TSV)),
        _ok("sb-tsv-write", "FACTKEY WROTE: k → docs/k.md", ["--write"], _small(_TSV), watch_files=("docs/k.md",)),
        _ok("sb-table-check", "", ["--check"], _small(_TABLE, sync=True)),
        _ok("sb-multi-target-check", "", ["--check"], _small(_MULTI, sync=True)),
        _ok("sb-rows-source-emit", "<!-- BEGIN GENERATED: fam -->", [], lambda r: (src(r), _small(_RS)(r))),
        _ok("sb-empty-registry", "", [], _small({})),
        _ok("sb-root-env", "", ["--check"], _small(_TSV, sync=True), env={"GOVB1_FACTKEY_ROOT": "."}),
    ]


def _key_order() -> List[fo.Case]:
    reg = {"zeta": {"target": "docs/z.md", "rows": [["001", "z"]]},
           "_schema": _MIN_SCHEMA,
           "alpha": {"target": "docs/a.md", "rows": [["001", "a"]]},
           "mid-9": {"target": "docs/m.md", "rows": [["001", "m"]]},
           "mid-10": {"target": "docs/m.md", "rows": [["001", "n"]]}}
    return [_ok("key-order-emit", "<!-- BEGIN GENERATED: alpha -->", [], _small(reg)),
            _ok("key-order-write", "FACTKEY WROTE: alpha → docs/a.md", ["--write"], _small(reg), watch_files=("docs/z.md", "docs/a.md", "docs/m.md"))]


def _bytes() -> List[fo.Case]:
    def add_id(d: dict) -> None:
        d["governance-worklist"]["rows"].append(["999", "WL-識別碼", "未開工", "FKPERF 探針"])
    doc = "前WL-識別碼後 未開工\n_WL-識別碼 未開工\nxWL-識別碼 未開工\n"
    return [
        fo.Case("bytes-multibyte-id", ("--check",), _tree(_reg(add_id), _sync, _write("白話說明/mb.md", doc)), 1, "FACTKEY HANDWRITTEN STATUS: 白話說明/mb.md:1 識別碼=WL-識別碼 狀態=未開工"),
        _ok("bytes-write-watch", "FACTKEY WROTE: committee-roster → docs/MULTI_AGENT_ORCHESTRATION.md", ["--write"], _tree(_cell("eventscan-banner", "字面", "改寫後之字面 α")),
            watch_files=("docs/EVENTSCAN_SPEC.md",)),
        _ok("bytes-backslash-cell", "<!-- BEGIN GENERATED: committee-roster -->", [], _tree(_cell("eventscan-banner", "字面", "a\\b 反斜線"))),
        _ok("bytes-case-sort", "<!-- BEGIN GENERATED: committee-roster -->", [], _tree(_reg(lambda d: d["eventscan-banner"]["rows"].extend(
            [["998", "b", "x", "y"], ["998", "B", "x", "y"], ["998", "É", "x", "y"]])))),
    ]


CORPUS: Dict[str, Callable[[], List[fo.Case]]] = {
    "exit": lambda: [c for _, c in EXIT_CASES],
    "real": _real,
    "sandbox": _sandbox,
    "key_order": _key_order,
    "bytes": _bytes,
}
