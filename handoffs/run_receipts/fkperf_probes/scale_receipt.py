"""FKPERF Task 4.4：四規模（1×／4×／10×／40×）× 五模式（emit、--check、--write、--status-hits、guard）各量三次耗時
與外部程序數，寫收據 `handoffs/run_receipts/<日期>-fkperf-scale.json`。沿用 `tests/governance/_fkperf_spawn.py` 之
建樹與量測 helper（與規模驗收測試同一實作）；合成註冊表只存在於系統 tmp，程序結束即刪。"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tests.governance import _fkperf_spawn as sp  # noqa: E402

MODES = ("emit", "--check", "--write", "--status-hits", "guard")


def main() -> None:
    c = sp.load_contract()
    rows = []
    tmp = Path(tempfile.mkdtemp(prefix="fkperf_scale_"))
    try:
        for label, total in c["scale_total_keys"].items():
            if total is None:  # 1× ＝ 目前真實註冊表之 key 總數（同 test_fkperf_scale._targets）
                total = sp.total_key_count(REPO)
            root = sp.build_scaled_tree(tmp / label, total)
            (root / "lines.txt").write_text("L1\tHP-FKPERF 已完成\n", encoding="utf-8")  # --status-hits 之行檔（同規模測試）
            for mode in MODES:
                secs = sp.time_mode(root, mode, 3)
                spawns = sp.count_spawns(root, mode)[0]
                rows.append({"scale": label, "total_keys": total, "mode": mode,
                             "seconds": [round(s, 4) for s in secs], "min_seconds": round(min(secs), 4),
                             "spawns": spawns})
                print(label, mode, round(min(secs), 3), spawns, flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(sp.write_receipt(rows, "fkperf-scale"))


if __name__ == "__main__":
    main()
