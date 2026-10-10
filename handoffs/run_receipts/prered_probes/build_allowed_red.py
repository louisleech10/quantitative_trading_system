"""由 red census 機械產生 allowed_red.json（PRE-RED Task 3.1，重凍後狀態）。
用法：python build_allowed_red.py <red_census.txt> <out.json>
固定列：frame manifest、IC-first 兩支、多週期基準與 config_hash 釘值（F-2）；census 中其餘失敗＝刪除舊特徵 run 所致（FFSTORE）。
"""

import json
import sys

FE = "tests/feature_engineering"
FIXED = [
    (f"{FE}/test_failopen_manifest.py::test_persist_false_generate_features_metadata", "FRAMEPATH", "user-ruling",
     "FFACT_USE_CGSA=0 之 frame 路徑；2026-09-28 使用者裁定刪除 frame 產生路徑；FRAMEPATH（第 5 步）收案時刪本列"),
    (f"{FE}/test_b6_warmup_trim.py::test_warmup_trim_ic_first", "ICFIRSTALIGN", "blocked-by",
     "run_ic_first 之 IC 階段讀回時間軸對齊（AlignmentViolationError）；ICFIRSTALIGN 乙（第 4 步）修復後刪本列"),
    (f"{FE}/test_b6_warmup_trim.py::test_warmup_trim_ic_first_public_window_init", "ICFIRSTALIGN", "blocked-by",
     "同上；ICFIRSTALIGN 乙收案時刪本列"),
    (f"{FE}/test_failopen_correctness.py::test_v3_multi_tf_btc_matches_frozen_baseline", "ICFIRSTALIGN", "blocked-by",
     "多週期基準於本機受 F-2（12h＋1h 全史預熱被系統終止）擋、未重凍；ICFIRSTALIGN 乙 MEM-RSS 修復後重凍多週期單元並刪本列"),
    (f"{FE}/test_failopen_producer.py::test_quality_gate_max_ratios_do_not_change_config_hash", "ICFIRSTALIGN", "blocked-by",
     "釘值改讀多週期基準之 config_hash（PRE-RED Task 2.6）；多週期單元重凍後轉綠並刪本列"),
]
_V6 = ("多週期 12h＋1h 於 d229336e 後全史預熱致峰值 footprint 約 71 GB、本機被系統終止（d229336e^ 同測試 1 passed、峰值 0.80 GB）＝F-2；"
       "ICFIRSTALIGN 乙 MEM-RSS 修復後刪本列")
FIXED += [(f"{FE}/test_failopen_correctness.py::{n}", "ICFIRSTALIGN", "blocked-by", _V6) for n in (
    "test_v6_independent_asof_oracle_matches_multi_tf_columns",
    "test_v6_backend_output_matches_independent_oracle[False]",
    "test_v6_backend_output_matches_independent_oracle[True]",
    "test_v6_close_time_oracle_matches_pipeline[False]",
    "test_v6_close_time_oracle_matches_pipeline[True]",
)]
DELETION_TRIGGER = ("使用者 2026-10-03 核可刪除全部舊算法特徵 run（data_cache/features）；FFSTORE（第 14 步）以新算法產新快照後，"
                    "改寫本測試之資料參照並刪本列")


def main(census: str, out: str) -> None:
    fixed_nodes = {n for n, *_ in FIXED}
    failed = []
    for line in open(census, encoding="utf-8"):
        if line.startswith(("FAILED ", "ERROR ")):
            node = line.split(" ", 1)[1].strip()
            if node not in fixed_nodes:
                failed.append(node)
    rows = [{"node": n, "owner_ticket": o, "reason": r, "state": "owned-by-later-ticket", "trigger": t} for n, o, r, t in FIXED]
    rows += [{"node": n, "owner_ticket": "FFSTORE", "reason": "user-ruling", "state": "owned-by-later-ticket",
              "trigger": DELETION_TRIGGER} for n in sorted(set(failed))]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("rows", len(rows), "deletion", len(set(failed)))


if __name__ == "__main__":
    main(*sys.argv[1:])
