#!/usr/bin/env python3
"""SPLITUNIFY B2c：golden 五組之凍結與比對（SPEC §G）。

用法：
    venv/bin/python scripts/freeze_splitunify_golden.py            # 比對模式（預設）
    venv/bin/python scripts/freeze_splitunify_golden.py --write    # 凍結／重凍

🔴 **比對失敗不得自動 `--write` 覆蓋**（SPEC Task 2.3 之「不可做」）——那等於沒有 golden。
🔴 **失敗必須指名差在哪一筆**，不得只回布林（B2b review 之教訓：只回真假的檢查
   等於把「哪裡壞了」丟給下一個人重查）。

五組（SPEC §G）：
  G-1  成員集合：`assignments`／`purged` 之 event_id 集合。
  G-3a **一次性遷移報告**：舊 `split_events` vs 新投影之差集 → `handoffs/run_receipts/`，
       🔴 **不進**預設比對綠徑（凍結一份「預期有差」的 golden 會把已知錯誤合法化）。
  G-3b **長期 golden**：新投影 vs **獨立 oracle**（直接由 `feature_index[plan.row_index]`
       投影出的 event_id 集合），要求集合相等。oracle 與被測函式無因果關係。
  G-4  per-symbol counts（整數逐值相等）。
  G-5  containment 四項：逐 row test fingerprint（sha256）、逐 event assignments／purged IDs、
       answer-window 完整性、leakage negative case。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from momentum.Analysis.event_samples.event_split import split_events  # noqa: E402
from momentum.Analysis.event_samples.split_projection import (  # noqa: E402
    derive_event_split_from_plans,
)
from momentum.Analysis.event_samples.types import (  # noqa: E402
    EventManifest,
    EventSplitConfig,
)
from momentum.core.contracts import SplitPlan  # noqa: E402
from momentum.core.split_preview import (  # noqa: E402
    build_row_time_fingerprint,
    holdout_boundary,
)

GOLDEN_DIR = REPO / "tests" / "golden" / "splitunify"
RECEIPT_DIR = REPO / "handoffs" / "run_receipts"

H1 = 3_600_000
BASE = 1_700_000_000_000
N_BARS = 200
OOS, PURGE, EMBARGO = 0.3, 2, 2
SYM = "ETHUSDT"


# ── fixture（固定、可重現；不依賴 data_cache）────────────────────────────
def _feature_index() -> pd.Index:
    return pd.Index([BASE + i * H1 for i in range(N_BARS)], dtype="int64")


def _plans(index: pd.Index):
    b = holdout_boundary(index, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)
    kw = dict(index_kind="positional", purge_gap=PURGE, embargo=EMBARGO,
              purge_semantic="rows", base_universe_hash="splitunify-golden", symbol=SYM)
    # 🔴 SPLITUNIFY D-001 (4.3)：本 fixture 之 index 即該 symbol 自己的索引（單標的）⇒
    #    `row_index_local` 逐值等於 `row_index`；指紋走**與 producer 同一支**序列化器。
    ms = np.asarray(index, dtype="int64")

    def _fp(rows: Any) -> str:
        loc = np.asarray(rows, dtype=int)
        return build_row_time_fingerprint(
            positions=loc, feature_ts_ms=ms[loc],
            symbol=SYM, base_universe_hash="splitunify-golden",
        )

    train = SplitPlan(split_label="train", row_index=b["train_row_index"],
                      time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])),
                      row_index_local=np.asarray(b["train_row_index"], dtype=int),
                      row_time_fingerprint=_fp(b["train_row_index"]), **kw)
    test = SplitPlan(split_label="test", row_index=b["test_row_index"],
                     time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])),
                     row_index_local=np.asarray(b["test_row_index"], dtype=int),
                     row_time_fingerprint=_fp(b["test_row_index"]), **kw)
    return train, test, b


def _event_keys(index: pd.Index, b: Dict[str, Any]) -> pd.DataFrame:
    """固定 12 筆：train 段 5（其中 1 筆答案窗跨界）、隔離區 2、test 段 5。"""
    tr, te = b["train_row_index"], b["test_row_index"]
    test_start = int(index[te[0]])
    rows: List[dict] = []
    for i, pos in enumerate(tr[:4]):
        rows.append((f"tr{i}", int(index[pos]), int(index[pos]) + H1))
    rows.append(("tr_leak", int(index[tr[-1]]), test_start))          # 答案窗恰好觸到 ⇒ purge
    for i in (1, 2):                                                   # 隔離區
        rows.append((f"gap{i}", int(index[tr[-1]]) + i * H1, int(index[tr[-1]]) + (i + 2) * H1))
    for i, pos in enumerate(te[:5]):
        rows.append((f"te{i}", int(index[pos]), int(index[pos]) + H1))
    return pd.DataFrame([
        {"event_id": e, "feature_cutoff_ms": c, "label_start_ms": c,
         "label_end_ms": le, "symbol": SYM, "timeframe": "1h"}
        for e, c, le in rows
    ])


def _manifest(keys: pd.DataFrame) -> EventManifest:
    return EventManifest(
        table=pd.DataFrame({
            "event_id": keys["event_id"], "symbol": keys["symbol"],
            "timeframe": keys["timeframe"],
            "decision_at_ms": keys["feature_cutoff_ms"].astype("int64"),
            "label_start_ms": keys["label_start_ms"].astype("int64"),
            "label_end_ms": keys["label_end_ms"].astype("int64"),
        }),
        summary={"n_events_raw": len(keys), "n_events_effective": len(keys)},
        policy={},
    )


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ── 獨立 oracle（G-3b／G-5②）：不呼叫被測函式 ──────────────────────────
def _oracle_membership(index: pd.Index, b: Dict[str, Any], keys: pd.DataFrame) -> Dict[str, list]:
    """直接由 `feature_index[row_index]` 投影出成員集合——與被測函式無因果關係。

    🔴 刻意**逐行重寫**兩段式規則（不 import 投影）：oracle 的價值就在於它是**第二份推導**，
    共用實作就退化成同義反覆（B2b review `CODEX-R1-P2-05` 之教訓）。
    """
    ms = np.asarray(index, dtype="int64")
    train_ms = set(ms[np.asarray(b["train_row_index"], dtype=int)].tolist())
    test_ms = set(ms[np.asarray(b["test_row_index"], dtype=int)].tolist())
    test_start = int(ms[int(np.asarray(b["test_row_index"], dtype=int)[0])])
    train, test, purged = [], [], []
    for rec in keys.to_dict("records"):
        cut, end = int(rec["feature_cutoff_ms"]), int(rec["label_end_ms"])
        in_train, in_test = cut in train_ms, cut in test_ms
        if in_train and end >= test_start:
            purged.append(rec["event_id"])
        elif in_test:
            test.append(rec["event_id"])
        elif in_train:
            train.append(rec["event_id"])
        else:
            purged.append(rec["event_id"])
    return {"train": sorted(train), "test": sorted(test), "purged": sorted(purged)}


def _build_actual() -> Dict[str, Any]:
    index = _feature_index()
    train_plan, test_plan, b = _plans(index)
    keys = _event_keys(index, b)
    man = _manifest(keys)
    plan = derive_event_split_from_plans(
        train_plan, test_plan, keys, index, manifest=man, bucket_ms=H1
    )
    a = plan.assignments
    ms = np.asarray(index, dtype="int64")
    test_rows = np.asarray(b["test_row_index"], dtype=int)

    # G-5① 逐 row test fingerprint：canonical (position, feature_ts_ms, symbol, universe_hash)
    # 🔴 SPLITUNIFY D-001-C2：欄名以 `feature_ts_ms` 為準（舊稱 `ts_ms`／`row_pos` 一律不得再用，
    #    含變數名與註解）；序列化規則與 `split_preview.build_row_time_fingerprint` **逐字同形**。
    fingerprint_rows = [
        [int(p), int(ms[p]), SYM, "splitunify-golden"] for p in test_rows
    ]
    return {
        # G-1
        "g1_membership": {
            "train": sorted(a.loc[a["split_label"] == "train", "event_id"]),
            "test": sorted(a.loc[a["split_label"] == "test", "event_id"]),
            "purged": sorted(plan.purged["event_id"]),
        },
        # G-3b oracle（獨立推導）
        "g3b_oracle": _oracle_membership(index, b, keys),
        # G-4 per-symbol counts（整數逐值相等）
        "g4_per_symbol_n": {k: int(v) for k, v in plan.summary["per_symbol_n"].items()},
        # G-5①
        # 🔴 SPLITUNIFY D-001-C2 第 7 點：獨立 oracle 與 producer 必須**同一支**序列化器，
        #    否則兩邊各凍一份、永遠不等。實測本呼叫與原本的 `_sha(fingerprint_rows)`
        #    逐位元同值（ascending positions 下 argsort 為恆等），故 golden 摘要不位移。
        "g5_row_fingerprint_sha256": build_row_time_fingerprint(
            positions=test_rows,
            feature_ts_ms=ms[test_rows],
            symbol=SYM,
            base_universe_hash="splitunify-golden",
        ),
        "g5_row_fingerprint_n": len(fingerprint_rows),
        # 🔴 B2c review `CODEX-R1-P1-02`：只凍 hash ⇒ **錯的 fingerprint 也會被自凍結**，
        #    測試只驗「是 64 位 hex」等於沒驗。⇒ 一併凍**明文** positions 與首尾時間戳，
        #    測試端據此**獨立重算** sha256 並逐值比對；失敗時指名第一個 mismatch 的 position。
        "g5_row_fingerprint_positions": [int(p) for p in test_rows],
        "g5_row_fingerprint_first_ms": int(ms[test_rows[0]]),
        "g5_row_fingerprint_last_ms": int(ms[test_rows[-1]]),
        # G-5③ answer-window 完整性：**兩端** endpoint 都須落在 source bars（＝ universe）內。
        # 🔴 B2c review：我原本只驗 `label_start_ms`，三家獨立命中「弱於 SPEC §G」——
        #    off-bar 的**終點**仍可留在 test assignments，而 SPEC 要求缺 endpoint 必 purge。
        "g5_answer_window": _answer_window_report(keys, a, plan.purged, set(ms.tolist())),
        "purge_reasons": sorted(set(plan.purged["reason"])),
    }


def _answer_window_report(
    keys: pd.DataFrame, assignments: pd.DataFrame, purged: pd.DataFrame, universe: set
) -> Dict[str, list]:
    """G-5③：逐事件驗 answer-window 之 **兩端** endpoint 是否都落在 source bars 上。

    🔴 **這裡驗的是「前置條件」，不是「投影有沒有 purge 它」**——兩者不同，別搞混：
    SPEC 之 R4／F1 明訂 endpoint 檢查**不進投影簽名**（投影沒有 bars，硬加會逼實作端發明
    第三個參數），改為「上游 alignment 之可證明前置條件」，G-5③ 用 golden 驗它。
    我第一版寫成「缺 endpoint **必 purge**」，與該裁定**互相矛盾**——投影根本不做這件事，
    那個斷言永遠只會在資料變髒時把矛頭指向投影。已改為驗前置條件本身。

    回三個集合：`both_endpoints_on_bar`、`missing_endpoint`、
    `precondition_breaches`（＝`missing_endpoint`，明示語意：上游該擋而沒擋）。
    """
    _ = (assignments, purged)  # 前置條件與歸屬無關；保留簽名供未來 R-5 支援時擴充
    both, missing = [], []
    for rec in keys.to_dict("records"):
        eid = rec["event_id"]
        on_bar = (int(rec["label_start_ms"]) in universe) and (int(rec["label_end_ms"]) in universe)
        (both if on_bar else missing).append(eid)
    return {
        "both_endpoints_on_bar": sorted(both),
        "missing_endpoint": sorted(missing),
        "precondition_breaches": sorted(missing),
    }


def _leakage_negative_case() -> str:
    """G-5④：把一筆 train 事件的 `label_end_ms` 推進 test 區 ⇒ **必進 purged**。

    回 `"ok"` 或失敗描述。這是 golden 的**負向**那一半——正向全對但負例不擋，
    等於沒有 containment 保證。
    """
    index = _feature_index()
    train_plan, test_plan, b = _plans(index)
    keys = _event_keys(index, b)
    test_start = int(np.asarray(index, dtype="int64")[int(np.asarray(b["test_row_index"])[0])])
    injected = keys.copy()
    target = injected.index[injected["event_id"] == "tr0"][0]
    injected.loc[target, "label_end_ms"] = test_start + H1  # 推進 test 區
    plan = derive_event_split_from_plans(
        train_plan, test_plan, injected, index, manifest=_manifest(injected), bucket_ms=H1
    )
    if "tr0" not in set(plan.purged["event_id"]):
        return "FAIL: 注入跨界之 train 事件 tr0 **未進 purged**（containment 已失效）"
    if "tr0" in set(plan.assignments["event_id"]):
        return "FAIL: tr0 同時留在 assignments"
    return "ok"


def _migration_report() -> Dict[str, Any]:
    """G-3a：舊 `split_events` vs 新投影之差集（**一次性遷移報告，不進綠徑**）。"""
    index = _feature_index()
    train_plan, test_plan, b = _plans(index)
    keys = _event_keys(index, b)
    man = _manifest(keys)
    new = derive_event_split_from_plans(
        train_plan, test_plan, keys, index, manifest=man, bucket_ms=H1
    )
    old = split_events(man, EventSplitConfig(test_fraction=0.3, bucket_ms=H1,
                                             tier_min_test_events=0))
    new_test = set(new.assignments.loc[new.assignments["split_label"] == "test", "event_id"])
    old_test = set(old.assignments.loc[old.assignments["split_label"] == "test", "event_id"])
    diff_ids = sorted((new_test - old_test) | (old_test - new_test))
    return {
        "_doc": "G-3a 一次性遷移報告：舊 split_events 與新投影**預期不等價**（SPEC C-2）。"
                "本檔記錄『差在哪』，**不進**預設比對綠徑——凍結一份預期有差的 golden "
                "會把已知錯誤合法化（B2b review GROK-R1-P1-03／COMPOSER-R1-P1-03）。",
        "only_in_new_test": sorted(new_test - old_test),
        "only_in_old_test": sorted(old_test - new_test),
        "diff_event_ids_sha256": _sha(diff_ids),
        "diff_cardinality": len(diff_ids),
    }


def _fingerprint_diff(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """G-5① 專用：hash 不等時**指名第一個 mismatch 的 position**（SPEC §G 逐字要求）。

    🔴 B2c review `GROK-R1-P2-02`：只回「sha256 不等」會把定位成本丟回給下一個人。
    """
    exp_pos = expected.get("g5_row_fingerprint_positions")
    got_pos = actual.get("g5_row_fingerprint_positions")
    if exp_pos is None or got_pos is None or exp_pos == got_pos:
        return []
    for i, (e, g) in enumerate(zip(exp_pos, got_pos)):
        if e != g:
            return [f"g5_row_fingerprint: 第一個 mismatch 在 index {i}（golden position={e} 實際={g}）"]
    longer = "實際" if len(got_pos) > len(exp_pos) else "golden"
    return [
        f"g5_row_fingerprint: 前 {min(len(exp_pos), len(got_pos))} 個 position 相同，"
        f"但 {longer} 多出 {abs(len(got_pos) - len(exp_pos))} 個"
    ]


def _diff_report(expected: Dict[str, Any], actual: Dict[str, Any]) -> List[str]:
    """逐鍵比對；**指名差在哪一筆**，不只回布林。"""
    problems: List[str] = list(_fingerprint_diff(expected, actual))
    for key in sorted(set(expected) | set(actual)):
        if key.startswith("_"):
            continue
        exp, got = expected.get(key), actual.get(key)
        if exp == got:
            continue
        if isinstance(exp, dict) and isinstance(got, dict):
            for sub in sorted(set(exp) | set(got)):
                e, g = exp.get(sub), got.get(sub)
                if e == g:
                    continue
                if isinstance(e, list) and isinstance(g, list):
                    problems.append(
                        f"{key}.{sub}: 只在 golden={sorted(set(e) - set(g))}；"
                        f"只在實際={sorted(set(g) - set(e))}"
                    )
                else:
                    problems.append(f"{key}.{sub}: golden={e} 實際={g}")
        elif isinstance(exp, list) and isinstance(got, list):
            problems.append(
                f"{key}: 只在 golden={sorted(set(exp) - set(got))}；"
                f"只在實際={sorted(set(got) - set(exp))}"
            )
        else:
            problems.append(f"{key}: golden={exp} 實際={got}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="凍結／重凍（比對失敗時**不得**自動用）")
    args = ap.parse_args()

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDEN_DIR / "splitunify_golden.json"
    actual = _build_actual()

    # G-3b：新投影 vs 獨立 oracle，集合相等（**每次都驗**，不只在凍結時）
    if actual["g1_membership"] != actual["g3b_oracle"]:
        for line in _diff_report(actual["g3b_oracle"], actual["g1_membership"]):
            print(f"  ✗ G-3b（獨立 oracle）: {line}")
        print("G-3b FAIL：投影與獨立 oracle 不一致")
        return 1
    print("  ✓ G-3b：投影與獨立 oracle 集合相等")

    # G-5④ leakage negative case（**每次都驗**）
    aw = actual["g5_answer_window"]
    if aw["precondition_breaches"]:
        print(
            "  ✗ G-5③（前置條件）：answer-window 兩端不都在 bar 上的事件 "
            f"{aw['precondition_breaches']}——上游 alignment 應已擋下（SPEC R4 之 F1）"
        )
        return 1
    print(
        f"  ✓ G-5③（前置條件）：{len(aw['both_endpoints_on_bar'])} 筆事件之 answer-window "
        "兩端皆在 bar 上"
    )

    neg = _leakage_negative_case()
    if neg != "ok":
        print(f"  ✗ G-5④ leakage negative case: {neg}")
        return 1
    print("  ✓ G-5④：注入跨界之 train 事件確實進 purged")

    if args.write:
        golden_path.write_text(
            json.dumps({"_doc": "SPLITUNIFY B2c golden（SPEC §G）。改動須經 review。",
                        **actual}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report = RECEIPT_DIR / "splitunify-g3a-migration-report.json"
        report.write_text(
            json.dumps(_migration_report(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  ✓ 已凍結 {golden_path.relative_to(REPO)}")
        print(f"  ✓ G-3a 遷移報告 → {report.relative_to(REPO)}（不進綠徑）")
        return 0

    if not golden_path.exists():
        print(f"GOLDEN MISSING: {golden_path.relative_to(REPO)}——首次請用 --write")
        return 1
    try:
        expected = json.loads(golden_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        # 🔴 B2c review `GROK-R1-P3-03`：原本讓裸 traceback 冒出來，
        #    與 `GOLDEN MISSING`／`GOLDEN MISMATCH` 不同級，看不出是 golden 壞了還是程式壞了。
        print(f"GOLDEN CORRUPT: {golden_path.relative_to(REPO)} 不是合法 JSON — {exc}")
        return 1
    if not isinstance(expected, dict) or not expected:
        print(f"GOLDEN CORRUPT: {golden_path.relative_to(REPO)} 為空或非物件")
        return 1
    problems = _diff_report(expected, actual)
    if problems:
        for line in problems:
            print(f"  ✗ {line}")
        print(f"GOLDEN MISMATCH: {len(problems)} 處（**不得**自動 --write 覆蓋）")
        return 1
    print("  ✓ G-1／G-4／G-5①③：golden 逐值相符")
    print("GOLDEN OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
