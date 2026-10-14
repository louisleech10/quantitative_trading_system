"""FRAMEPATH Task 1.5：由主委整併之決策檔產出 `tests/_golden/framepath/test_disposition.json`。

輸入 `--decisions`（JSON）：{"operations": [...], "nodeid_reasons": {nodeid: 理由}, "new_files": [...],
"fact_key_rows": [...], "collect_extra": [...]}；每個操作：
  {"phase", "path", "kind", "frame_basis", "deleted_nodeids": [...], "renamed_nodeids": {舊: 新},
   + 種類專屬欄：locator／new_name／rewrite{reason, preserved_assertion_lines, removed_assertion_lines{行: 理由}, new_source}／
     pointer／new_content}
本工具只做機械衍生（不做處置判斷）：
- 母體＝HEAD 6e07e0ad 中 SPEC Task 1.5 所列字面任一命中之 tests／frontend/src／scripts 檔 ＋ extra，排除 fact_keys；
- collect 檔集合＝母體與操作表 path 中位於 tests/ 之 .py；nodeid 表＝其於 HEAD 碼態之 `pytest --collect-only`
  （主工作樹之 .py 與 6e07e0ad 相同，收據記錄核對）；
- 摘錄、摘錄雜湊、保留斷言雜湊、改寫後全文雜湊、replace-file 新檔雜湊：一律呼叫驗證器同一函式；
- ignored_baseline：於 `--clean-worktree`（當前提交之乾淨 detached worktree，非主工作樹）以 SPEC ⑤(b) 同一命令與
  副檔名／__pycache__ 過濾凍結（審查 r25 GROK-R25-P1-01；主工作樹之本機被忽略檔不得進基線）。
用法：PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/build_disposition.py --decisions <檔> --out <檔> \
      --clean-worktree <git worktree add --detach 之路徑>

重錨（SPEC v22 D11.2；只改處置表之 `rebase` 段，不改操作語意、不重產其他段）：
  PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/build_disposition.py --list-rebase-needed
      列出錨點以來曾被他票（D11.1）改過、本票有操作（任一 phase）、尚無重錨紀錄之治理檔，附衝突檢查結果。
  PYTHONPATH=. venv/bin/python handoffs/run_receipts/framepath_probes/build_disposition.py --rebase <治理檔> [--rebase …] \
      [--base-commit <rev>] [--table tests/_golden/framepath/test_disposition.json] --out <檔>
      新基準＝該檔於他票最近一次改動之提交（--base-commit 只准指定該提交本身）；拒絕：錨點至基準間有本票提交改該檔、
      基準後他票又改該檔、衝突檢查相交（他票改動之頂層定義／JSON pointer 與本票對該檔任一操作之目標相交）、操作於基準
      重新定位之摘錄與錨點不同。寫出前以驗證器之 rebase schema 與歷史核對自檢。重錨為獨立提交（處置表 sha256 改變 ⇒
      manifest contract_sha256 與逐項閱讀視圖須同提交更新），審碼核對。
  全表產生模式不保留 `rebase` 段（SPEC v22 D11.11(d)）；重錨一律走 --rebase。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

LITERALS = [
    "FFACT_USE_CGSA", "_cgsa_enabled", "_generate_multi_tf_legacy", "_legacy_native_row_maps", "load_factory_output",
    "save_factory_output", "_factory.h5", "_factory_meta.json", "_try_load_cache", "_load_hdf5_features",
    "register_hdf5_for_browse", "multi_tf_legacy_merged", "multi_tf_layers", "multi_symbol_c3", "batch2d/control",
    "hdf5_path", "hdf5_relative_path", ".h5",
    # SPEC v17 B5（Task 2.5–2.8；使用者 2026-10-08 擴大刪除面）
    "persist_registry_to_parquet", "stream_groups(", "load_manifest(", "list_features(", "load_columns(",
    "load_cross_symbol", "AsyncParquetCompactor", "FFACT_L7_WORKERS", "FFACT_L7_COMPACTOR", "l7_workers",
    "migrate_d_star_cache", "FFACT_DSTAR_CACHE_MIGRATE_LEGACY", "export_for_ml", "enable_hdf5_cache",
    "hdf5_cache_compression", "FFACT_HDF5_CHUNK", "legacy_v7", "feature_file_exists", "list_feature_files",
    "delete_features", "_adapt_legacy_manifest_v2", "parquet:",
]
ROOTS = ["tests", "frontend/src", "scripts"]
EXTRA = ["tests/governance/test_prered_allowed_red.py"]
EXCLUDED = ["scripts/fact_keys.json"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def population(head: str) -> list:
    cmd = ["grep", "-l", "-F"] + [x for lit in LITERALS for x in ("-e", lit)] + [head, "--", *ROOTS]
    # 實作期 b1：非 ASCII 路徑須關 core.quotepath，否則 git grep 輸出帶引號與八進位逸出（母體路徑失真）
    out = subprocess.run(["git", "-c", "core.quotepath=off", *cmd], cwd=REPO, capture_output=True, text=True)
    files = {line.split(":", 1)[1] for line in out.stdout.splitlines() if line}
    files |= set(EXTRA)
    return sorted(files - set(EXCLUDED))


def clean_ignored(wt: Path) -> list:
    if subprocess.run(["git", "-C", str(wt), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout:
        raise SystemExit(f"--clean-worktree 非乾淨：{wt}")
    out = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(wt), "ls-files", "--others", "--ignored", "--exclude-standard", "--", *V.R_ROOTS],
                         capture_output=True, text=True, check=True).stdout
    return V._filter_ignored(out.splitlines())


def _file_history(anchor: str, path: str) -> list:
    """錨點至 HEAD 間改過 path 之提交（時間序）：[(sha, 是否本票提交)]（D11.1）。"""
    log = V.commit_log(V.REPO, f"{anchor}..HEAD", path, reverse=True)
    return [(sha, mine) for sha, mine, paths in V.parse_commit_log(log) if path in paths]


def rebase_needed(disp: dict) -> list:
    foreign, _ticket = V.foreign_and_ticket_paths()
    op_paths = {op["path"] for op in disp["operations"]}
    done = set(disp.get("rebase") or {})
    return sorted(p for p in V.governed_files(disp) if p in foreign and p in op_paths and p not in done)


def plan_rebase(disp: dict, path: str, base_rev: str = None) -> dict:
    """單檔重錨之機械檢查與紀錄（不寫檔）；任一條件不成立 ⇒ SystemExit。"""
    anchor = disp["head_commit"]
    if path not in V.governed_files(disp):
        raise SystemExit(f"{path} 不在治理檔（母體 ∪ 操作表 path）")
    hist = _file_history(anchor, path)
    foreign = [sha for sha, mine in hist if not mine]
    if not foreign:
        raise SystemExit(f"{path}：錨點以來無他票提交改過，不需重錨")
    base = foreign[-1]
    if base_rev is not None and git("rev-parse", base_rev).strip() != base:
        raise SystemExit(f"{path}：--base-commit 須為他票最近一次改動之提交 {base[:8]}（新基準定義，SPEC v22 D11.2）")
    upto = hist[: [sha for sha, _ in hist].index(base) + 1]
    mine = [sha[:8] for sha, m in upto if m]
    if mine:
        raise SystemExit(f"{path}：錨點至基準間有本票提交改此檔 {mine}——重錨只准吸收他票改動，須重新處置並經審查")
    ops = [op for op in disp["operations"] if op["path"] == path]
    anchor_b = V.HeadReader(anchor).read(path)
    base_b = V._git_show_bytes(base, path)
    conflicts = V.rebase_conflicts(path, anchor_b, base_b, ops)
    if conflicts:
        raise SystemExit("衝突檢查相交（fail-closed，須重新處置並經審查）：\n  " + "\n  ".join(conflicts))
    if path.endswith(".py") and any(op["kind"] in V.PY_KINDS for op in ops):
        try:
            V.rebase_ops(anchor_b.decode("utf-8"), base_b.decode("utf-8"), ops)
        except (SyntaxError, V.LocatorError) as exc:
            raise SystemExit(f"{path}：操作於基準無法重新定位：{exc}")
    return {"base_commit": base, "foreign_commits": [sha for sha, _ in upto]}


def main_rebase(args) -> int:
    table = Path(args.table)
    disp = json.loads(table.read_text(encoding="utf-8"))
    if args.list_rebase_needed:
        for p in rebase_needed(disp):
            anchor = disp["head_commit"]
            ops = [op for op in disp["operations"] if op["path"] == p]
            hist = _file_history(anchor, p)
            foreign = [sha for sha, m in hist if not m]
            if not foreign:  # 路徑限定之 log 看不到他票提交（如改名）⇒ 具名列出，不猜
                print(f"{p}\tops=…\thistory={[(s[:8], m) for s, m in hist]}\tconflict=unknown（路徑限定 log 無他票提交）")
                continue
            conflicts = V.rebase_conflicts(p, V.HeadReader(anchor).read(p), V._git_show_bytes(foreign[-1], p), ops)
            print(f"{p}\tops={','.join(op['id'] + '@p' + str(op['phase']) for op in ops)}\t"
                  f"history={','.join(sha[:8] + ('(本票)' if m else '(他票)') for sha, m in hist)}\t"
                  f"conflict={'; '.join(conflicts) if conflicts else 'none'}")
        return 0
    rebase = dict(disp.get("rebase") or {})
    for path in args.rebase:
        rebase[path] = plan_rebase(disp, path, args.base_commit)
        print(f"{path}\tbase={rebase[path]['base_commit'][:8]}\tforeign={[c[:8] for c in rebase[path]['foreign_commits']]}")
    disp["rebase"] = {p: rebase[p] for p in sorted(rebase)}
    errs = V.rebase_schema_errors(disp) + V.rebase_history_errors(disp, V.REPO, disp["head_commit"])
    if errs:
        raise SystemExit("自檢不過：\n  " + "\n  ".join(errs))
    Path(args.out).write_text(json.dumps(disp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions")
    ap.add_argument("--out")
    ap.add_argument("--clean-worktree")
    ap.add_argument("--rebase", action="append", default=[], help="重錨之治理檔（可重複；SPEC v22 D11.2）")
    ap.add_argument("--base-commit", help="重錨基準（須為他票最近一次改動該檔之提交；預設即該提交）")
    ap.add_argument("--table", default=str(REPO / V.DISPOSITION_REL))
    ap.add_argument("--list-rebase-needed", action="store_true")
    args = ap.parse_args()
    if args.rebase or args.list_rebase_needed:
        if args.rebase and not args.out:
            ap.error("--rebase 須搭配 --out")
        if args.base_commit and len(args.rebase) != 1:
            ap.error("--base-commit 只能搭配單一 --rebase")
        return main_rebase(args)
    if not (args.decisions and args.out and args.clean_worktree):
        ap.error("全表產生須 --decisions、--out、--clean-worktree")
    dec = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    head = git("rev-parse", V.HEAD_SHORT).strip()
    reader = V.HeadReader(head)
    pop = population(head)

    # 核對：主工作樹 .py 與 HEAD 相同（collect 於主工作樹執行之前提）
    drift = [p for p in git("diff", "--name-only", head, "--", "*.py").splitlines() if p and not p.startswith("handoffs/")]
    new_paths = {item["path"] for item in dec["new_files"]}
    drift = [p for p in drift if p not in new_paths]
    if drift:
        raise SystemExit(f"主工作樹 .py 與 HEAD 不同：{drift}")

    ops = []
    for i, d in enumerate(dec["operations"], 1):
        op = {"id": f"OP-{i:03d}", "phase": d["phase"], "path": d["path"], "kind": d["kind"],
              "excerpt_sha256": "", "excerpt": "", "frame_basis": d["frame_basis"],
              "nodeids": sorted(set(d.get("deleted_nodeids", [])) | set(d.get("renamed_nodeids", {})))}
        hb = reader.read(d["path"])
        if hb is None:
            raise SystemExit(f"{op['id']} {d['path']} 於 HEAD 不存在")
        if d["kind"] in V.PY_KINDS:
            op["locator"] = d["locator"]
            src = hb.decode("utf-8")
            if d["kind"] == "rename":
                op["new_name"] = d["new_name"]
            if d["kind"] == "rewrite":
                rw = d["rewrite"]
                new_def = V.parse_rewrite_source(rw["new_source"])
                pres = V.preserved_assertion_dumps(src, [{"lineno": n} for n in rw["preserved_assertion_lines"]])
                op["rewrite"] = {
                    "reason": rw["reason"],
                    "preserved_assertions": [{"lineno": n, "ast_sha256": V.sha256_text(dump)} for n, dump in pres],
                    "removed_assertions": [
                        {"lineno": n, "ast_sha256": V.sha256_text(dump), "reason": rw["removed_assertion_lines"][str(n)]}
                        for n, dump in V.preserved_assertion_dumps(
                            src, [{"lineno": int(k)} for k in rw.get("removed_assertion_lines", {})])],
                    "new_source": rw["new_source"],
                    "new_source_ast_sha256": V.sha256_text(V.ast_dump(new_def)),
                }
            op["excerpt"] = V.excerpt_text_py(src, op)
            op["excerpt_sha256"] = V.excerpt_hash_py(src, op)
        elif d["kind"] == "delete-json-path":
            op["pointer"] = d["pointer"]
            op["excerpt"] = V.canonical_json(V.json_resolve(json.loads(hb), d["pointer"])).decode("utf-8")
            op["excerpt_sha256"] = V.excerpt_hash_json(hb, d["pointer"])
        elif d["kind"] == "replace-file":
            op["new_content"] = d["new_content"]
            op["new_sha256"] = V.sha256_text(d["new_content"])
            op["excerpt"] = "（整檔，見 HEAD）"
            op["excerpt_sha256"] = V.sha256_bytes(hb)
        else:
            op["excerpt"] = "（整檔，見 HEAD）"
            op["excerpt_sha256"] = V.sha256_bytes(hb)
        ops.append(op)

    collect_files = sorted({p for p in set(pop) | {o["path"] for o in ops} | set(dec.get("collect_extra", []))
                            if p.startswith("tests/") and p.endswith(".py") and reader.read(p) is not None})
    head_nodeids = sorted(V.collect_nodeids(collect_files))
    by_nodeid = {}
    for op in ops:
        d = dec["operations"][int(op["id"][3:]) - 1]
        for nid in d.get("deleted_nodeids", []):
            by_nodeid[nid] = {"disposition": "delete", "op": op["id"], "phase": op["phase"]}
        for old, new in d.get("renamed_nodeids", {}).items():
            by_nodeid[old] = {"disposition": "rename", "op": op["id"], "phase": op["phase"], "new_nodeid": new}
    unknown = sorted(set(by_nodeid) - set(head_nodeids))
    if unknown:
        raise SystemExit(f"決策列之 nodeid 不在 HEAD collect：{unknown[:20]}")
    rows = []
    for nid in head_nodeids:
        if nid in by_nodeid:
            b = by_nodeid[nid]
            row = {"nodeid": nid, "phase": b["phase"], "disposition": b["disposition"], "op": b["op"]}
            if b["disposition"] == "delete":
                row["reason"] = dec["nodeid_reasons"].get(nid) or next(
                    o["frame_basis"] for o in ops if o["id"] == b["op"])
            else:
                row["new_nodeid"] = b["new_nodeid"]
            rows.append(row)
        else:
            rows.append({"nodeid": nid, "phase": 1, "disposition": "keep"})

    disp = {
        "schema": "framepath-test-disposition/1",
        "head_commit": head,
        "python": "%d.%d" % sys.version_info[:2],
        "spec": "docs/FRAMEPATH_SPEC.md v16 Task 1.5",
        "population": {"roots": ROOTS, "literals": LITERALS, "extra": EXTRA, "excluded": EXCLUDED,
                       "command": "git grep -l -F <literals> 6e07e0ad -- tests frontend/src scripts", "files": pop},
        "collect": {"command": "python -m pytest --collect-only -q -o addopts=--import-mode=importlib -p no:cacheprovider <files>",
                    "files": collect_files},
        "hash_algorithms": {
            "py": "ast.dump(node, annotate_fields=True, include_attributes=False) 之 utf-8 sha256；dict 項以 Dict(keys=[k], values=[v]) 傾印；定位一律對 HEAD 版",
            "json": "目標子樹之 json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False) utf-8 sha256",
            "file": "HEAD 整檔位元組 sha256",
            "module_compare": "兩側經 strip_ffact（SPEC Task 1.5 驗證末段 (a)–(d)）後之 ast.dump 逐字相等",
            "definition": "tests/feature_engineering/test_framepath_disposition.py",
        },
        "nodeids": rows,
        "operations": ops,
        "new_files": dec["new_files"],
        "fact_key_rows": dec["fact_key_rows"],
        "ignored_baseline": clean_ignored(Path(args.clean_worktree)),
    }
    Path(args.out).write_text(json.dumps(disp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"population={len(pop)} collect_files={len(collect_files)} nodeids={len(rows)} ops={len(ops)} "
          f"delete={sum(r['disposition']=='delete' for r in rows)} rename={sum(r['disposition']=='rename' for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
