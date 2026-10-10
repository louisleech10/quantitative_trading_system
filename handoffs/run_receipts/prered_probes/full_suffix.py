"""PRE-RED 探針：判定兩版之改變是否「只把前段改為 NaN」（兩趟）。

趟 1（新版 worktree）：venv/bin/python <本檔> out <map.json>
    逐層逐欄記 fv（首個有限值列；全 NaN＝列數）與 sha(float64(v[fv:]))。
趟 2（舊版 worktree）：venv/bin/python <本檔> in <map.json> <result.json>
    以新版之 fv 取舊版同名欄 sha(float64(v[fv:]))；相等＝該欄只多遮前段（或不變）；
    不等＝遮罩後數值有變（列入 value_changed，附欄名）。只出現在單側之欄另計。
與 _single_tf_record 同流程（BTCUSDT/12h；凍結腳本本體），須 PYTHONHASHSEED=0。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
LAYERS = ["L1", "L2", "L3", "L4", "L5", "L6", "final_L7"]


def _run(collect) -> None:
    import numpy as np  # noqa: F401

    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    orig = freeze._hash_registry_table
    calls = {"i": 0}

    def _spy(registry, groups, index):
        rec = orig(registry, groups, index)
        layer = LAYERS[calls["i"]] if calls["i"] < len(LAYERS) else f"extra{calls['i']}"
        calls["i"] += 1
        for g in freeze._ordered_groups(registry, groups):
            data = np.asarray(registry.load_data_native(g.group_id))
            for i, name in enumerate(g.columns):
                collect(layer, str(name), np.asarray(data[:, i], dtype=np.float64))
        return rec

    import numpy as np

    freeze._hash_registry_table = _spy
    with tempfile.TemporaryDirectory() as tmp:
        freeze._single_tf_record("BTCUSDT", "12h", Path(tmp))


def _sha(v) -> str:
    import numpy as np

    c = np.array(v, copy=True)
    c[np.isnan(c)] = np.nan
    return hashlib.sha256(c.tobytes()).hexdigest()[:20]


def main() -> int:
    assert os.environ.get("PYTHONHASHSEED") == "0"
    import numpy as np

    mode = sys.argv[1]
    if mode == "dump":
        # dump <layer> <npz>：該層全部欄之 float64 陣列
        want, arrays = sys.argv[2], {}

        def collect(layer, name, v):
            if layer == want:
                arrays[name] = v

        _run(collect)
        np.savez_compressed(sys.argv[3], **arrays)
        print("dumped", want, len(arrays))
        return 0
    if mode == "out":
        out: dict = {}

        def collect(layer, name, v):
            finite = ~np.isnan(v)
            fv = int(np.argmax(finite)) if finite.any() else len(v)
            out.setdefault(layer, {})[name] = [fv, _sha(v[fv:])]

        _run(collect)
        Path(sys.argv[2]).write_text(json.dumps(out), encoding="utf-8")
        print("out layers", {k: len(v) for k, v in out.items()})
        return 0

    ref = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    res: dict = {}

    def collect(layer, name, v):
        r = res.setdefault(layer, {"prefix_or_same": 0, "value_changed": [], "only_old": [], "new_fv_earlier": []})
        new = ref.get(layer, {}).get(name)
        if new is None:
            r["only_old"].append(name)
            return
        fv, h = new
        finite = ~np.isnan(v)
        old_fv = int(np.argmax(finite)) if finite.any() else len(v)
        if old_fv > fv:
            r["new_fv_earlier"].append(name)
        if _sha(v[fv:]) == h:
            r["prefix_or_same"] += 1
        else:
            r["value_changed"].append(name)

    _run(collect)
    for layer, r in res.items():
        r["only_new"] = sorted(set(ref.get(layer, {})) - set(r["only_old"]) - set(
            n for n in ref.get(layer, {}) if False))
    summary = {layer: {"prefix_or_same": r["prefix_or_same"], "value_changed": len(r["value_changed"]),
                       "only_old": len(r["only_old"]), "new_fv_earlier": len(r["new_fv_earlier"])}
               for layer, r in res.items()}
    Path(sys.argv[3]).write_text(json.dumps({"summary": summary, "detail": res}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
