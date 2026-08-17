"""主委自產（R9 段 C-1 先答）：A1-11 之 AST wiring 規則有無可執行假綠路徑。

規則原型（依 TODO Task 2.4 步驟 1）：
  parse report.py → 找 FunctionDef build_validation_section → 取其 Return 的 ast.Dict 鍵
  ＋ body 內對該 dict 的 Constant 鍵指派 ⇒ assembled 集合。
本探針對 6 種真實會出現的組裝寫法檢查 assembled 是否完整（不完整＝W1 誤紅；
反之若把不存在的節算進來＝假綠）。
"""
import ast

PROTOTYPE_TARGET = "build_validation_section"


def assembled_keys(src: str) -> set:
    """規則原型實作（刻意照 TODO 字面，不多做）。"""
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == PROTOTYPE_TARGET), None)
    if fn is None:
        return set()
    keys = set()
    # (a) Return 的 dict 字面
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            for k in node.value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
    # (b) body 內 d["x"] = ... 形
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (isinstance(tgt, ast.Subscript) and isinstance(tgt.slice, ast.Constant)
                        and isinstance(tgt.slice.value, str)):
                    keys.add(tgt.slice.value)
    # (c) 函式內任意 dict 字面之 Constant 鍵（TODO 括號說明「含其函式 body 內…」）
    for node in ast.walk(fn):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
    return keys


CASES = {
    "1_直接 return dict 字面（規格預期形）": '''
def build_validation_section(*, eligibility, dsr, pbo, provenance):
    return {"eligibility": {}, "min_btl": {}, "dsr": {}, "pbo": {}, "provenance": {}}
''',
    "2_逐鍵指派": '''
def build_validation_section(**kw):
    out = {}
    out["eligibility"] = {}
    out["min_btl"] = {}
    out["dsr"] = {}
    out["pbo"] = {}
    out["provenance"] = {}
    return out
''',
    "3_helper 函式組裝（跨函式）": '''
def _sections(e, d, p):
    return {"eligibility": e, "min_btl": {}, "dsr": d, "pbo": p, "provenance": {}}

def build_validation_section(**kw):
    return _sections(kw["e"], kw["d"], kw["p"])
''',
    "4_迴圈＋變數鍵": '''
SECTION_NAMES = ("eligibility", "min_btl", "dsr", "pbo", "provenance")

def build_validation_section(**kw):
    out = {}
    for name in SECTION_NAMES:
        out[name] = {}
    return out
''',
    "5_dict(**展開)": '''
def build_validation_section(**kw):
    base = {"eligibility": {}, "min_btl": {}}
    rest = {"dsr": {}, "pbo": {}, "provenance": {}}
    return {**base, **rest}
''',
    "6_註解／docstring 假綠測試（只寫在字串裡，未組裝）": '''
def build_validation_section(**kw):
    """回傳 eligibility / min_btl / dsr / pbo / provenance 五節。"""
    # "pbo" 這個節其實沒組
    return {"eligibility": {}, "min_btl": {}, "dsr": {}, "provenance": {}}
''',
}

REQUIRED = {"eligibility", "min_btl", "dsr", "pbo", "provenance"}
print(f"契約 report_sections = {sorted(REQUIRED)}\n")
for name, src in CASES.items():
    got = assembled_keys(src)
    missing = REQUIRED - got
    verdict = "rc=0 綠" if not missing else f"rc=1 紅（缺 {sorted(missing)}）"
    print(f"{name}\n   assembled={sorted(got)}\n   → {verdict}")
