#!/usr/bin/env python
"""B-D5 mutation 自證：把生產碼逐條改壞，證明新測試會**紅**。

    venv/bin/python handoffs/20260906-gap3d2-b5-mutate.py

## 紀律（B-D1 兩次事故之修法，逐字沿用自 B-D4 腳本）

1. **還原權威＝版控**（`git checkout -- <檔>`），**不用自存備份**——備份會停在某個
   舊 commit，之後的改動會被它整段回捲，而腳本自己印 `restored`、沒有東西會紅。
2. **開場先檢查目標檔與 HEAD 一致**，不乾淨即 `exit 3` 拒跑（否則還原會吃掉未提交改動）。
   🔴 **檢查在任何清理／還原之前**——反過來就是「先還原（未提交的修正沒了）→ 再檢查乾淨
   （此時當然乾淨）→ 通過」，2026-09-04 一次沖掉四個檔的修正就是這個順序。
3. 每條 mutation 跑完立刻還原，再跑下一條。
4. 對照組（`EXPECT_GREEN`）證明腳本沒有把所有東西都弄紅。
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "venv" / "bin" / "python")


@dataclass(frozen=True)
class Mutation:
    mid: str
    path: str
    old: str
    new: str
    selector: List[str]
    why: str
    occurrences: int = 1


PYTEST = [PY, "-m", "pytest", "-q", "-x", "-p", "no:logging"]
T_CONTRACT = "tests/momentum/event_samples/test_import_contract.py"
T_RC = "tests/momentum/event_samples/test_random_control.py"
T_API = "tests/api/test_gap3_random_control.py"
T_REG = "tests/api/test_gap3_contract_reason_registry.py"
GOLDEN_LABEL = [PY, "scripts/gap3_label_golden.py", "--check", "tests/golden/gap3_label/*.json"]
GOLDEN_RC = [PY, "scripts/gap3_label_golden.py", "--kind", "random_control",
             "--check", "tests/golden/gap3_random_control/*.json"]

MUTATIONS: Tuple[Mutation, ...] = (
    # ── D5.1 契約／validator ────────────────────────────────────────────
    Mutation(
        "M1-required-false-fail-open",
        "momentum/Analysis/event_samples/import_contract.py",
        "            if _decl_required(sub):\n",
        "            if False:\n",
        [*PYTEST, T_CONTRACT, "-k", "unknown_and_missing_leaf"],
        "typed node 之必填葉缺席不再回報（鍵級 required 語義 fail-open）",
    ),
    Mutation(
        "M2-recursion-collapsed",
        "momentum/Analysis/event_samples/import_contract.py",
        "    if t not in _CONTAINER_TYPE_DECLS:\n",
        "    if True:\n",
        [*PYTEST, T_CONTRACT, "-k", "random_control"],
        "遞迴塌成 leaf（容器節點交給 receipt_type_ok ⇒ 未知字面）",
    ),
    Mutation(
        "M3-float-accepts-int",
        "momentum/Analysis/event_samples/import_contract.py",
        "        return type(value) is float\n",
        "        return isinstance(value, (int, float))\n",
        [*PYTEST, T_CONTRACT, "-k", "typed_leaf_paths"],
        "`float` 放行 int（0 與 0.0 位元組不同 ⇒ 規則身分 digest 分裂）",
    ),
    Mutation(
        "M4-spec-missing-not-enforced",
        "momentum/Analysis/event_samples/import_contract.py",
        "    if is_random_batch and random_control_spec is None:\n",
        "    if False:\n",
        [*PYTEST, T_CONTRACT, "-k", "requires_batch_level_spec"],
        "隨機批缺抽樣契約不再拒收（宣稱是對照組卻無從重現）",
    ),
    Mutation(
        "M5-mixed-batch-not-enforced",
        "momentum/Analysis/event_samples/import_contract.py",
        "    if _RANDOM_KIND in control_kinds and not is_random_batch:\n",
        "    if False:\n",
        [*PYTEST, T_CONTRACT, "-k", "mixed_without_spec"],
        "隨機列可搭觸發批偷渡（prevalence 分母不再是無條件基準）",
    ),
    Mutation(
        "M6-label-origin-mixed-not-enforced",
        "momentum/Analysis/event_samples/import_contract.py",
        '        if r.get("label_origin") == _RANDOM_ORIGIN and r.get("control_kind") != _RANDOM_KIND:\n',
        "        if False:\n",
        [*PYTEST, T_CONTRACT, "-k", "platform_random_on_trigger_batch"],
        "`label_origin=platform_random` 與 control_kind 脫鉤",
    ),
    Mutation(
        "M7-label-rule-reason-collapsed",
        "momentum/Analysis/event_samples/import_contract.py",
        '"random_control_label_rule_missing",\n                 "random_control_spec 缺 label_rule',
        '"missing_required_field",\n                 "random_control_spec 缺 label_rule',
        [*PYTEST, T_CONTRACT, "-k", "spec_missing_label_rule"],
        "label_rule 缺席之專屬 reason 塌回泛用字面（下游分不出是哪種缺）",
    ),
    Mutation(
        "M8-control-kind-not-accepted",
        "momentum/Analysis/contracts/event_import_contract.json",
        # 🔴 錨點須含 `"accepted":` 前綴：同一串值也出現在 `enum` 那行，
        #    只比對值會命中兩處，連 enum 一起改掉就不是「只收回 accepted」這條 mutation 了。
        '"accepted": ["user_labeled_same_trigger", "user_labeled_other", '
        '"platform_same_trigger_rule", "platform_random_bars"]',
        '"accepted": ["user_labeled_same_trigger", "user_labeled_other", '
        '"platform_same_trigger_rule"]',
        [*PYTEST, T_CONTRACT, "-k", "requires_batch_level_spec"],
        "契約把 `platform_random_bars` 收回 accepted（解禁被回捲）",
    ),
    Mutation(
        "M9-batch-optional-becomes-required",
        "momentum/Analysis/contracts/event_import_contract.json",
        '"required": false,\n        "doc": "D-001 D5.1：**觸發批之規則身分**',
        '"required": true,\n        "doc": "D-001 D5.1：**觸發批之規則身分**',
        [*PYTEST, T_REG, "-k", "08b or 08d"],
        "`batch.label_rule` 之鍵級 required:false 被改成必填（舊批全部變違規）",
    ),

    # ── D5.2 產生器 ────────────────────────────────────────────────────
    Mutation(
        "M10-exclusion-off-by-one",
        "momentum/Analysis/event_samples/random_control.py",
        "        mask[lo:hi + 1] = True\n",
        "        mask[lo:hi] = True\n",
        [*PYTEST, T_RC, "-k", "outside_every_exclusion or golden_check"],
        "排除區間右端少一根（對照組偷到答案窗末根，值仍合法）",
    ),
    Mutation(
        "M11-neighborhood-ignored",
        "momentum/Analysis/event_samples/random_control.py",
        "        lo = max(0, t0_pos - neighborhood)\n",
        "        lo = max(0, t0_pos)\n",
        [*PYTEST, T_RC, "-k", "neighborhood_changed or counterexample_zero_neighborhood"],
        "前鄰域參數被無視（`neighborhood_bars` 形同虛設）",
    ),
    Mutation(
        "M12-seed-ignored",
        "momentum/Analysis/event_samples/random_control.py",
        # R1 閉合後 seed 先經 `_require_int` ⇒ 錨點更新（原 `int(spec["seed"])` 已不存在）
        "    rng = np.random.default_rng(seed)\n",
        "    rng = np.random.default_rng(0)\n",
        [*PYTEST, T_RC, "-k", "seed_changed_digest_differs or golden_check"],
        "seed 被無視（不同 seed 抽出同一批，決定性宣稱失效）",
    ),
    Mutation(
        "M13-allocate-uses-round",
        "momentum/Analysis/event_samples/random_control.py",
        "        base = int(math.floor(exact))\n",
        "        base = int(round(exact))\n",
        [*PYTEST, T_RC, "-k", "allocate_pure_function"],
        "配額改用 round（`D-001` D5.2 明令禁止；和可能超過 n_target）",
    ),
    Mutation(
        "M14-allocate-tiebreak-reversed",
        "momentum/Analysis/event_samples/random_control.py",
        "    order = [k for _, k in sorted(fracs, key=lambda x: (-x[0], x[1]))]\n",
        "    order = [k for _, k in sorted(fracs, key=lambda x: (x[0], x[1]))]\n",
        [*PYTEST, T_RC, "-k", "allocate_pure_function"],
        "最大餘數序反轉（餘額給小數最小的層）",
    ),
    Mutation(
        "M15-eligibility-bypassed",
        "momentum/Analysis/event_samples/random_control.py",
        "        if _ab._is_eligible(i, n_rows, horizon, 0, open_, close, open_ms, step_ms) is not None:\n",
        "        if False:\n",
        [*PYTEST, T_RC, "-k", "same_eligibility"],
        "候選不再過同一支 eligibility（對照組與處理組分母不同）",
    ),
    Mutation(
        "M16-direction-sign-fixed-long",
        "momentum/Analysis/event_samples/random_control.py",
        '    sign = 1.0 if direction == "long" else -1.0\n',
        "    sign = 1.0\n",
        [*PYTEST, T_RC, "-k", "short_direction_flips_sign"],
        "short 批不取負（方向被吃掉，label 與 label_value 皆錯）",
    ),
    Mutation(
        "M17-horizon-fail-open",
        "momentum/Analysis/event_samples/random_control.py",
        '    if type(out["horizon_bars"]) is not int or out["horizon_bars"] < 1:\n',
        "    if False:\n",
        [*PYTEST, T_RC, "-k", "label_rule_shape_fail_closed"],
        "`horizon_bars` 形狀不再 fail-closed（0 長答案窗放行）",
    ),
    Mutation(
        "M18-label-comparison-inverted",
        "momentum/Analysis/event_samples/all_bars_eval.py",
        # R1 閉合後 `label_from_signed_return` 已移除（失去唯一呼叫端）⇒ 錨點回到 `_label_from_rule`
        "    return int(r >= threshold)\n",
        "    return int(r <= threshold)\n",
        [*PYTEST, T_RC, "-k", "golden_check"],
        "標籤比較式反向（唯一比較式被改壞 ⇒ 兩條路徑一起錯）",
    ),
    Mutation(
        "M19-period-check-removed",
        "momentum/Analysis/event_samples/random_control.py",
        "    if per_hi < trig_lo or per_lo > trig_hi:\n",
        "    if False:\n",
        [*PYTEST, T_RC, "-k", "period_disjoint_raises"],
        "period 交集檢查移除（拿不同時期的基準當對照）",
    ),

    # ── D5.3 服務／端點 ────────────────────────────────────────────────
    Mutation(
        "M20-gate1-identity-skipped",
        "api/services/ic_analysis_service.py",
        "        if trig_rule is None:\n",
        "        if False and trig_rule is None:\n",
        [*PYTEST, T_API, "-k", "compare_i_identity_unverifiable"],
        "規則身分閘①移除（沒有規則身分也照樣並排 prevalence）",
    ),
    Mutation(
        "M21-gate2-leaf-compare-skipped",
        "api/services/ic_analysis_service.py",
        "        if trig_leaves != rand_leaves:\n",
        "        if False:\n",
        [*PYTEST, T_API, "-k", "compare_ii_leaf_mismatch"],
        "規則身分閘②之逐葉比對移除（兩把尺不同也算成立）",
    ),
    Mutation(
        "M22-gate2-mode-check-skipped",
        "api/services/ic_analysis_service.py",
        "        if str(trig_mode) != _IDENTITY_LABEL_RETURN_MODE:\n",
        "        if False:\n",
        [*PYTEST, T_API, "-k", "compare_iib_trigger_mode"],
        "觸發批之 `label_return_mode` 不再受檢（open_to_* 也拿來比）",
    ),
    Mutation(
        "M23-gate3-reeval-skipped",
        "api/services/ic_analysis_service.py",
        "        if n_agree != n_checked:\n",
        "        if False:\n",
        [*PYTEST, T_API, "-k", "compare_iv_mutation_flipped"],
        "規則身分閘③之重評移除（宣告的規則與落檔答案不符也放行）",
    ),
    Mutation(
        "M24-receipt-validation-skipped",
        "api/services/case_import_service.py",
        '            if not outcome["ok"]:\n',
        "            if False:\n",
        [*PYTEST, T_API, "-k", "roundtrip_rejects_bad_spec or envelope_rejects_bad"],
        "receipt.batch 落檔前之 typed 驗被跳過（壞形狀直接寫進磁碟）",
    ),
    Mutation(
        "M25-detail-projection-dropped",
        "api/services/case_import_service.py",
        "                random_control_spec=dict(rcs) if isinstance(rcs, dict) else None,\n",
        "                random_control_spec=None,\n",
        [*PYTEST, T_API, "-k", "roundtrip_spec_survives_storage"],
        "detail 不投影抽樣契約（落檔了但讀不回來＝靜默丟欄）",
    ),

    # ── D5.4 golden ───────────────────────────────────────────────────
    Mutation(
        "M26-kind-default-flipped",
        "scripts/gap3_label_golden.py",
        'ap.add_argument("--kind", choices=_KINDS, default="label",',
        'ap.add_argument("--kind", choices=_KINDS, default="random_control",',
        GOLDEN_LABEL,
        "`--kind` 預設值改掉 ⇒ 既有 46 檔之驗收命令會走到別的 loader",
    ),
    Mutation(
        "M27-golden-drift-guard-removed",
        "scripts/gap3_label_golden.py",
        "            drift = guard(case, item)\n",
        "            drift = None\n",
        [*PYTEST, T_RC, "-k", "cli_detects_registry_drift"],
        "登記處漂移對證被拿掉（改了 selector 後重凍會靜默失去覆蓋）",
    ),

    # ── 前端 ───────────────────────────────────────────────────────────
    Mutation(
        "M28-period-not-derived",
        "frontend/src/lib/randomControlSpec.ts",
        "  const period = { start_ms: Math.min(...t0s), end_ms: Math.max(...t0s) };\n",
        "  const period = { start_ms: 0, end_ms: 0 };\n",
        ["npx", "vitest", "run", "icRandomControl"],
        "universe／period 不再由批次事實導出（抽樣母體與觸發期脫鉤）",
    ),
    Mutation(
        "M29-batch-rule-ignored",
        "frontend/src/lib/randomControlSpec.ts",
        "  const threshold = batchRule ? batchRule.threshold : params.threshold;\n",
        "  const threshold = params.threshold;\n",
        ["npx", "vitest", "run", "icRandomControl"],
        "批之落檔規則身分被 UI 輸入蓋掉（兩批用不同門檻而畫面說一樣）",
    ),
    Mutation(
        "M30-button-sends-empty-spec",
        "frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx",
        "                    event_import_id: importId, random_control_spec: randomSpec.spec,\n",
        "                    event_import_id: importId, random_control_spec: {},\n",
        ["npx", "vitest", "run", "icRandomControl"],
        "按鈕沒把純函式組出來的 spec 送出（幽靈接線：畫得出來、送出去是空的）",
    ),

    # ── R1 閉合之四條（三家 findings） ─────────────────────────────────
    Mutation(
        "M33-compare-not-wired-frontend",
        "frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx",
        "                    setRcCompare(verdict);\n",
        "                    void verdict;\n",
        ["npx", "vitest", "run", "icRandomControl"],
        "R1 三家命中：產完對照批不跑（或不顯示）規則身分閘 ⇒ 使用者拿不到結論",
    ),
    Mutation(
        "M34-sample-design-always-case-control",
        "api/services/ic_analysis_service.py",
        '        return RANDOM_SAMPLE_DESIGN if kinds == {"platform_random_bars"} else "case_control"\n',
        '        return "case_control"\n',
        [*PYTEST, T_API, "-k", "standalone_ic_analysis_sample_design"],
        "R1 `GROK-R1-P2-01`：抽樣設計揭露恆為 case_control ⇒ 無條件估計被讀成條件估計",
    ),
    Mutation(
        "M35-int-coercion-restored",
        "momentum/Analysis/event_samples/random_control.py",
        "    if type(value) is not int:\n",
        "    if False:\n",
        [*PYTEST, T_API, "-k", "rejects_non_exact_int"],
        "R1 `CODEX-R1-P1-02`：非 exact int 又被靜默 coerce（receipt 與 request 不同）",
    ),
    Mutation(
        "M36-gate3-trusts-label-value",
        "api/services/ic_analysis_service.py",
        '            lv_ok = lv is None or float(lv) == got["signed_return"]\n',
        "            lv_ok = True\n",
        [*PYTEST, T_API, "-k", "gate3_reads_bar_table"],
        "R1 `COMPOSER-R1-P1-02`：閘③又回去信任 label_value（與 bar 表不符也放行）",
    ),
    Mutation(
        "M37-gate3-label-check-removed",
        "api/services/ic_analysis_service.py",
        '            if got["label"] == int(lab) and lv_ok:\n',
        "            if True:\n",
        [*PYTEST, T_API, "-k", "compare_iv_mutation_flipped or gate3_reads_bar_table"],
        "閘③之重評比對整段失效（宣告與落檔不符也算一致）",
    ),

    # ── 對照組（預期綠）────────────────────────────────────────────────
    Mutation(
        "M31-control-comment-only",
        "momentum/Analysis/event_samples/random_control.py",
        "#: 本產生器之版本字面（進 receipt；抽樣演算法改動須改此值，否則 golden 無從辨別）。\n",
        "#: （對照組：只改註解）\n",
        [*PYTEST, T_RC, "-k", "same_seed_same_digest or golden_check"],
        "（對照組：只改註解 ⇒ 應綠，證明腳本不是把所有東西都弄紅）",
    ),
    Mutation(
        "M32-control-frontend-comment",
        "frontend/src/lib/randomControlSpec.ts",
        "/** 抽樣契約之 `allocation` 封閉單值（後端契約定死；此處為鏡像，由測試對證）。 */\n",
        "/** （對照組：只改註解） */\n",
        ["npx", "vitest", "run", "icRandomControl"],
        "（對照組：前端只改註解 ⇒ 應綠）",
    ),
)

#: 對照組（預期**綠**）之 id。
EXPECT_GREEN = {"M31-control-comment-only", "M32-control-frontend-comment"}


def _run(cmd: List[str], cwd: Path) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *paths],
        cwd=str(REPO), capture_output=True, text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    targets = sorted({m.path for m in MUTATIONS})
    # 🔴 開場檢查（在任何寫檔／還原**之前**）
    dirty = _dirty(targets)
    if dirty:
        print(f"REFUSE rc=3：目標檔與 HEAD 不一致 {dirty}——先 commit，否則還原會吃掉未提交改動")
        return 3

    results: List[Tuple[str, int, bool]] = []
    for m in MUTATIONS:
        p = REPO / m.path
        src = p.read_text(encoding="utf-8")
        if m.old not in src:
            print(f"SKIP {m.mid}: 找不到目標字串（生產碼已改？）")
            results.append((m.mid, -1, False))
            continue
        assert src.count(m.old) == m.occurrences, (
            f"{m.mid}: 目標字串出現 {src.count(m.old)} 處，宣告 {m.occurrences} 處"
        )
        p.write_text(src.replace(m.old, m.new), encoding="utf-8")
        cwd = REPO / "frontend" if m.selector[0] == "npx" else REPO
        rc = _run(m.selector, cwd)
        subprocess.run(["git", "checkout", "--", m.path], cwd=str(REPO), check=True)
        want_green = m.mid in EXPECT_GREEN
        ok = (rc == 0) if want_green else (rc != 0)
        results.append((m.mid, rc, ok))
        print(f"{'PASS' if ok else 'FAIL'} {m.mid} rc={rc} "
              f"（期望 {'綠' if want_green else '紅'}）— {m.why}")

    # 還原後必須乾淨
    left = _dirty(targets)
    print(f"\nRESTORED clean={not left} {left}")
    bad = [r for r in results if not r[2]]
    print(f"SUMMARY {len(results) - len(bad)}/{len(results)} 條符合預期")
    return 0 if (not bad and not left) else 1


if __name__ == "__main__":
    sys.exit(main())
