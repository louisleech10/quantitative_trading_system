"""對候選處置表跑驗證器之 schema／③／④（與 HEAD 對照之內部一致性），不需 manifest。用法：check_disp.py <disp.json>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tests.feature_engineering import test_framepath_disposition as V  # noqa: E402

disp = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
spec = (V.REPO / "docs/FRAMEPATH_SPEC.md").read_text(encoding="utf-8")
head = V.HeadReader(disp["head_commit"])
errs = V.schema_errors(disp, spec) + V.check_3(disp, 3, head) + V.check_4(disp, head)
for op in disp["operations"]:
    if head.obj_type(op["path"]) == "tree" or not V.kind_ext_ok(op["kind"], op["path"]):
        errs.append(f"kind/ext {op['id']}")
# 模擬 HEAD 套用全表後各 py 檔可解析、且 rename 新名存在
for path in sorted({op["path"] for op in disp["operations"] if op["kind"] in V.PY_KINDS}):
    ops = [op for op in disp["operations"] if op["path"] == path and op["kind"] in V.PY_KINDS]
    try:
        V.apply_py_ops(head.read(path).decode(), ops)
    except Exception as exc:  # noqa: BLE001
        errs.append(f"apply {path}: {exc}")
print(len(errs))
print("\n".join(errs[:60]))
