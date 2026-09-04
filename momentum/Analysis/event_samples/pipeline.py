"""GAP-3 事件樣本組合殼（docs/GAP3_EVENT_TODO.md Task B5.1）：validate → align → dedupe → split → materialize。

服務端**唯一**消費入口（`momentum/factories.create_event_sample_pipeline()` 出口）。本檔只組合 B1 純函式、不重複實作
任何檢查（R7：契約驗證唯一實作＝`import_contract.validate_event_import`）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.Analysis.event_samples.alignment import align_events, n_dropped_by_reason
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.feature_materialization import materialize_features_at_decision
from momentum.Analysis.event_samples.import_contract import ContractValidationError, validate_event_import
from momentum.Analysis.event_samples.lookahead_gate import LookaheadGate, assert_split_allowed
from momentum.Analysis.event_samples.types import (
    AlignmentConfig, AlignmentReceipts, DedupePolicyConfig, EventManifest, EventSplitConfig, EventSplitPlan,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class EventPipelineConfig:
    """組合殼設定（全部轉交 B1 各 dataclass；無新字面）。

    timeframes：需 per-TF 收據之 TF 清單（空 ⇒ 只錨定 TF）。
    cluster_gap_ms：B1.2 簇間隔（None ⇒ 答案窗）。
    split：B1.3 切分設定。
    feature_config：B1.6 設定（None ⇒ 不物化特徵）。
    """

    timeframes: Tuple[str, ...] = ()
    cluster_gap_ms: Optional[int] = None
    split: EventSplitConfig = field(default_factory=EventSplitConfig)
    feature_config: Optional[dict] = None


@dataclass
class EventPipelineResult:
    """一次 run 的全部產出（各層記帳守恆：n_events == n_receipts + n_align_failures）。"""

    events: pd.DataFrame
    receipts: AlignmentReceipts
    align_failures: pd.DataFrame
    manifest: EventManifest
    split_plan: Optional[EventSplitPlan]   # None ＝ Task 1.12 之 event-study-only（未執行切分）
    features: Optional[pd.DataFrame]
    feature_manifest_hash: Optional[str]
    feature_failures: Optional[pd.DataFrame]
    summary: Dict[str, Any]


class EventSamplePipeline:
    """validate→align→dedupe→split→materialize 組合殼（純組合；不 log hot loop）。"""

    # ---- 契約唯讀出口（R3：api 層只經 factories 一個出口取得 pipeline，再由此讀契約；不直 import momentum 內部）----
    @staticmethod
    def import_contract() -> dict:
        """事件匯入契約 JSON（SoT；唯讀拷貝）。"""
        from momentum.Analysis.event_samples.import_contract import load_event_import_contract

        return load_event_import_contract()

    @staticmethod
    def canonical_event_id(symbol, timeframe, t0, *, contract: Optional[dict] = None) -> str:
        """GAP-3 UX Task 1.3／D-2：`event_id` 之唯一實作出口（R3：api 層不直 import momentum 內部）。"""
        from momentum.Analysis.event_samples.import_contract import canonical_event_id as _impl

        return _impl(symbol, timeframe, t0, contract=contract)

    @staticmethod
    def event_id_template(contract: Optional[dict] = None) -> str:
        """`event_id` 公式之字面 SoT 出口（前端模板由測試對證本值逐字相等）。"""
        from momentum.Analysis.event_samples.import_contract import event_id_template as _impl

        return _impl(contract)

    @staticmethod
    def mapping_failure_reasons(contract: Optional[dict] = None) -> Dict[str, str]:
        """GAP-3 UX Task 1.2 對映層 reason 之具名出口（R3／R7：api 層只引用鍵，不複列字面）。"""
        from momentum.Analysis.event_samples.import_contract import mapping_failure_reasons as _impl

        return _impl(contract)

    @staticmethod
    def normalize_t0_units(records: List[dict], *, contract: Optional[dict] = None) -> None:
        """GAP-3 UX Task 1.4：就地正規化 `t0` 單位（唯一偵測函式＝`import_contract.detect_t0_unit_ms`）。

        R3：api 層不得直 import momentum 內部 ⇒ CSV 與 JSON 兩路徑皆經本出口取得同一實作。
        """
        from momentum.Analysis.event_samples.import_contract import normalize_t0_units as _impl

        _impl(records, contract=contract)

    @staticmethod
    def source_file_misupload_hint(content) -> Optional[str]:
        """GAP-3 UX Task 5.1：上傳內容若為 `*.source.json`，回正解提示字串；否則 `None`。

        R3：api 層不得直 import momentum 內部 ⇒ 判別與字面皆經本出口取得同一實作
        （JSON／CSV 兩條上傳路徑共用，不得為其中一條另寫一份）。
        """
        from momentum.Analysis.event_samples.import_contract import source_file_misupload_hint as _impl

        return _impl(content)

    @staticmethod
    def canonical_source_payload(cases) -> Tuple[str, str]:
        """GAP-3 UX Task 1.3：`/search` 結果列 → (`source_file_text`, `source_file_digest`)。

        序列化唯一實作＝`canonical_serialize.canonical_source_bytes`（§G S-9 第 7 條：禁複製邏輯）；
        `source_file_text` ＝該 exact bytes 之 UTF-8 解碼（**無尾端 newline**）。
        🔴 與 `rule_digest`（綁 `search_rule_summary`）為兩件事，本出口**不產出** rule_digest。
        """
        from momentum.Analysis.event_samples.canonical_serialize import canonical_source_bytes

        raw = canonical_source_bytes(cases)
        return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()

    @staticmethod
    def condition_engine_contract() -> dict:
        """條件引擎契約 JSON（含 `allowed_filtering_params`；深拷貝）。"""
        from momentum.Analysis.event_samples.condition_engine import load_condition_engine_contract

        return load_condition_engine_contract()

    # ---- GAP-3 UX Task 1.9／1.11／1.12：答案窗宣告與 L3 閘之 R3 出口（api 層不直 import momentum 內部）----
    @staticmethod
    def requires_lookahead_declaration(columns, timeframe, *, provenance=None) -> bool:
        """Task 1.11（L2）：這組**條件引用欄**在該 tf 是否強制使用者宣告深度。"""
        from momentum.Analysis.event_samples.lookahead_registry import (
            PROVENANCE_EXTERNAL_UPLOAD, requires_declaration as _impl,
        )

        return _impl(columns, timeframe, provenance=provenance or PROVENANCE_EXTERNAL_UPLOAD)

    @staticmethod
    def lookahead_declaration_defaults(data_columns, timeframes) -> Dict[str, int]:
        """Task 1.9 ①：逐 tf 之預設宣告值＝檔內最大可用 horizon（唯一實作在 lookahead_declaration）。"""
        from momentum.Analysis.event_samples.lookahead_declaration import default_window_bars_by_timeframe

        return default_window_bars_by_timeframe(data_columns, timeframes)

    @staticmethod
    def resolve_lookahead_declaration(records, *, data_columns, declaration) -> Dict[str, Any]:
        """Task 1.9／1.11：解析宣告、就地投影 `horizon_bars`、算 per-symbol embargo 下界。

        回**純資料**：成功 `{"ok": True, "receipt": {...}}`；不合規
        `{"ok": False, "kind": str, "message": str, "detail": {...}}`
        ——例外型別不跨界（R3：api 層不 import momentum 內部型別，亦不得 catch 它）。

        🔴 `timeframe_seconds` 於**本出口**注入（SPEC R22：換算 map 為注入值，非 module 常數之硬引用），
        api 層因此不需要、也不得自行 import `TIMEFRAME_SECONDS`。
        """
        from momentum.core.constants import TIMEFRAME_SECONDS
        from momentum.Analysis.event_samples.lookahead_declaration import (
            LookaheadDeclarationError, resolve_declaration,
        )

        try:
            outcome = resolve_declaration(records, data_columns=data_columns, declaration=declaration,
                                          timeframe_seconds=TIMEFRAME_SECONDS)
        except LookaheadDeclarationError as exc:
            return {"ok": False, "kind": exc.kind, "message": str(exc), "detail": exc.detail}
        return {"ok": True, "receipt": outcome.to_receipt()}

    @staticmethod
    def preview_lookahead_declaration(data_columns, timeframes, *, records=()) -> Dict[str, Any]:
        """Task 1.9 ①／1.9′：宣告框預填資料之 R3 出口（回純資料）。

        匯入端與匯出端**同一實作** `lookahead_declaration.preview_from_columns`（`CODEX-R35-P1-04`）；
        本出口不算深度、不重寫換算表。
        """
        from momentum.Analysis.event_samples.lookahead_declaration import preview_from_columns

        return dict(preview_from_columns(data_columns, timeframes, records=list(records)))

    @staticmethod
    def apply_lookahead_horizon_projection(rows, lookahead_bars_declared) -> int:
        """Task 1.9 ③：把 `max(1, depth[該列 tf])` 投影進 `label_definition.window.horizon_bars`。

        🔴 呼叫時機在 `validate()` **之後**（Task 1.8 同質檢查看的是使用者原列，見實作 docstring）。
        """
        from momentum.Analysis.event_samples.lookahead_declaration import apply_horizon_projection

        return apply_horizon_projection(rows, lookahead_bars_declared)

    @staticmethod
    def lookahead_split_blocked(receipt) -> bool:
        """Task 1.12：落檔批次是否被 L3 封鎖（analyze 之分派依據；回 bool，型別不跨界）。"""
        from momentum.Analysis.event_samples.lookahead_declaration import gate_from_receipt

        return bool(gate_from_receipt(receipt).blocked)

    @staticmethod
    def split_blocked_capability_reason() -> str:
        """Task 1.12 ②：L3 之 capability reason 字面（唯一來源＝契約之具名綁定）。"""
        from momentum.Analysis.event_samples.lookahead_gate import split_blocked_reason

        return split_blocked_reason()

    @staticmethod
    def validate_receipt_values(namespace: str, values: Mapping[str, Any], *,
                                contract: Optional[dict] = None) -> Dict[str, Any]:
        """Task 1.6：receipt namespace 之型別／齊備性驗證出口（R3；回**純資料**）。

        成功 `{"ok": True, "failures": []}`；不合規 `{"ok": False, "failures": [{row,event_id,field,reason}, …]}`
        ——reason 字面來自契約之封閉集合（`missing_required_field`／`type_error`／`unknown_field`），
        api 層不得複列，亦不得 catch `ContractValidationError`（例外型別不跨界）。

        🔴 驗證實作**唯一**住 `import_contract.validate_receipt_namespace`（與驗收共用同一函式參考）；
        本出口只做例外→純資料之轉換，不重寫任何判定。
        """
        from momentum.Analysis.event_samples.import_contract import (
            ContractValidationError as _CVE, validate_receipt_namespace as _impl,
        )

        try:
            _impl(namespace, values, contract=contract)
        except _CVE as exc:
            return {"ok": False, "failures": [dict(f) for f in exc.failures]}
        return {"ok": True, "failures": []}

    # ── GAP-3 UX Task 7.0b：分析時 label producer 之 R3 出口 ────────────────────
    # 🔴 **具名例外**：交接檔之 R3 慣例寫「出口一律回純資料，例外型別不跨界」，
    #    而下面三個出口會讓 `PreparedAnalysisWindows`（frozen dataclass）**跨界到 api 層**。
    #    這是刻意的、不是漏看：SPEC Task 7.0b ⑩(ii″) 要求 manifest／split／materialize／
    #    `ic_feed` 四處收到的物件**皆 `is prepared1`**——那是**身分**比對，dict 往返做不到。
    #    實查 `scripts/check_decoupling_imports.py`：R3 是 **import 規則 ＋ manifest 白名單**，
    #    **不驗回傳型別** ⇒ 機械閘不會紅。慣例確實被破，故在此與模組檔頭兩處具名。
    #    ⚠️ 例外只涵蓋這三個出口與 `PreparedAnalysisWindows`／`AnalysisLabelResult` 兩個型別；
    #    不得據此推廣到其他出口。

    @staticmethod
    def prepare_analysis_windows(records, bars_by_tf, *, event_label_spec, event_import_id,
                                 lookahead_bars_declared, timeframe_seconds):
        """Task 7.0b 階段 2 之 R3 出口（回 `PreparedAnalysisWindows`；見上方具名例外）。"""
        from momentum.Analysis.event_samples.label_value_from_case import (
            prepare_analysis_windows as _impl,
        )

        return _impl(
            records, bars_by_tf,
            event_label_spec=event_label_spec,
            event_import_id=event_import_id,
            lookahead_bars_declared=lookahead_bars_declared,
            timeframe_seconds=timeframe_seconds,
        )

    @staticmethod
    def resolve_label_value_at_analyze(prepared, bars_by_tf, *, event_label_spec):
        """Task 7.0b 階段 5 之 R3 出口（回 `AnalysisLabelResult`）。"""
        from momentum.Analysis.event_samples.label_value_from_case import (
            resolve_label_value_at_analyze as _impl,
        )

        return _impl(prepared, bars_by_tf, event_label_spec=event_label_spec)

    @staticmethod
    def apply_event_coverage(prepared, allowed_event_ids):
        """Task 7.0b 階段 3b 之 R3 出口（`dataclasses.replace`，回**新**物件、同 token 同 hash）。"""
        from momentum.Analysis.event_samples.label_value_from_case import (
            apply_event_coverage as _impl,
        )

        return _impl(prepared, allowed_event_ids)

    @staticmethod
    def timeframe_seconds_for(timeframes) -> Dict[str, int]:
        """Task 7.0b／7.7 之 `timeframe_seconds` **建構出口**（回純資料）。

        🔴 SPEC 定死「於匯入驗證通過後、prepare 之前**建構一次**，並以**同一物件**傳入
        `purge_lower_bound_ms` 與 feature-run gate（驗收以 `is` 比對）」。
        本出口存在的理由是讓 api 層**不必** import `momentum/core/constants.py::TIMEFRAME_SECONDS`
        ——那個常數是**建構素材**，SPEC 明禁 gate 內直讀它。由這裡建一次、回一個 dict，
        呼叫端把**同一個 dict** 往下傳，`is` 比對才有東西可比。

        缺鍵 ⇒ raise（不補預設）：不認得的 timeframe 無法換算 ms，猜一個等於算錯。
        """
        from momentum.core.constants import TIMEFRAME_SECONDS

        out: Dict[str, int] = {}
        for tf in timeframes:
            key = str(tf)
            if key not in TIMEFRAME_SECONDS:
                raise ValueError(
                    f"timeframe_seconds_for: 不認得的 timeframe {key!r}（fail-closed，不補預設）"
                )
            out[key] = int(TIMEFRAME_SECONDS[key])
        return out

    @staticmethod
    def event_context_for_analysis(prepared, records) -> Dict[str, str]:
        """survivor v2 六鍵 `event_context` 之 R3 出口（GAP-3 Task 7.0b 五階段；回純 dict）。

        唯一實作＝`ic_feed.event_context_from_windows`；`label_definition`／`control_kind` 取自本批 records，
        批內不唯一 ⇒ raise（契約同質檢查本應已擋；此處是第二道）。
        """
        from momentum.Analysis.event_samples.ic_feed import event_context_from_windows

        recs = list(records)
        lds = {json.dumps(r.get("label_definition"), sort_keys=True, separators=(",", ":")) for r in recs}
        cks = {str(r.get("control_kind")) for r in recs}
        if len(lds) != 1 or len(cks) != 1:
            raise ValueError(
                f"event_context_for_analysis: 批內 label_definition／control_kind 須唯一（得 {len(lds)}／{len(cks)} 組）"
            )
        return event_context_from_windows(
            prepared.windows, label_definition=json.loads(next(iter(lds))), control_kind=next(iter(cks)),
        )

    @staticmethod
    def supported_matrix_text() -> str:
        """§F-1′ 支援矩陣之**人可讀字面**（`G3-D2` D1.3 之 R3 出口）。

        🔴 為什麼要有這個出口：`api/` 不得 import `momentum`（Rule 3；
        `scripts/check_decoupling_imports.py` 會當場擋）。而錯誤訊息若在 `api/` 手寫
        支援域字面，矩陣一擴充那句就過期——使用者照著過期訊息去改設定會改錯。
        本函式回字串而非集合：呼叫端只需要顯示，不需要判定（判定一律走 `spec_is_supported`）。
        """
        from momentum.Analysis.event_samples.label_value_from_case import SUPPORTED_MATRIX

        return "、".join(f"({e}, {m}, k={k})" for e, m, k in sorted(SUPPORTED_MATRIX))

    @staticmethod
    def project_purge(purge_rows) -> Mapping[str, int]:
        """Task 7.0b 階段 4 之 R3 出口：`tuple[SymbolPurgeRow, ...]` → read-only `Mapping[str,int]`。

        🔴 這個出口**回純資料**（read-only Mapping），與上面三個不同——
        它是投影的邊界，本來就不該讓 receipt 型別跨過來。
        """
        from momentum.Analysis.event_samples.label_value_from_case import project_purge as _impl

        return _impl(purge_rows)

    @staticmethod
    def bars_from_kline_cache(symbols, timeframes, *, cache_path=None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """真實 kline bars（`bars_source.load_bars_from_kline_cache`）；服務端取 bars 的唯一入口。"""
        from momentum.Analysis.event_samples.bars_source import load_bars_from_kline_cache

        return load_bars_from_kline_cache(symbols, timeframes, cache_path=cache_path)

    def run_with_params(
        self, records, bars_by_tf, *, test_fraction: float = 0.3, embargo_ms: Optional[int] = None,
        tier_min_test_events: int = 1, timeframes: Tuple[str, ...] = (), cluster_gap_ms: Optional[int] = None,
    ) -> "EventPipelineResult":
        """純量參數版 `run`（服務端經 factories 出口呼叫、不 import momentum dataclass——R3/R7）。"""
        cfg = EventPipelineConfig(
            timeframes=tuple(timeframes), cluster_gap_ms=cluster_gap_ms,
            split=EventSplitConfig(test_fraction=float(test_fraction), embargo_ms=embargo_ms,
                                   tier_min_test_events=int(tier_min_test_events)),
        )
        return self.run(records, bars_by_tf, cfg)

    def run_event_study_only_with_params(
        self, records, bars_by_tf, *, timeframes: Tuple[str, ...] = (), cluster_gap_ms: Optional[int] = None,
        source_bytes: Optional[bytes] = None,
    ) -> "EventPipelineResult":
        """純量參數版 `run_event_study_only`（服務端不 import momentum dataclass——R3/R7）。

        🔴 **不吃 split 參數**：本路徑不切分，收 `test_fraction`／`embargo_ms` 只會讓呼叫端
        以為切分仍在進行。
        """
        cfg = EventPipelineConfig(timeframes=tuple(timeframes), cluster_gap_ms=cluster_gap_ms)
        return self.run_event_study_only(records, bars_by_tf, cfg, source_bytes=source_bytes)

    def analyze_tables(
        self, result: "EventPipelineResult", bars_by_tf: Dict[str, Dict[str, pd.DataFrame]], *,
        horizons: Tuple[int, ...] = (1, 2, 4), seed: int = 20260820, n_boot: int = 300,
    ) -> Dict[str, Any]:
        """B2 表：事件後報酬表（B2.1）＋全 K 線驗證（B2.5 `evaluate_all_bars`，rule＝事件成員：事件 t₀ 根 score=1、其餘 0）；
        辨別表需模型分數——無分數 ⇒ `not_computed`＋reason（前端顯示原因，不重算）。"""
        from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
        from momentum.Analysis.event_samples.tables import event_forward_return_table

        fwd = event_forward_return_table(result.manifest, result.receipts, bars_by_tf, result.split_plan,
                                         {"horizons": [int(h) for h in horizons], "seed": int(seed), "n_boot": int(n_boot)})
        disc = {"statistic_kind": "binary_discrimination", "capability_status": "not_computed",
                "reason": "no_model_scores_in_event_pipeline",
                "doc": "辨別表需 test 段模型分數（B4.1 pattern 橋或外部模型）；匯入管線本身不產分數，不在此重算統計"}
        all_bars = self._all_bars_for_events(result, bars_by_tf, seed=seed, n_boot=n_boot, evaluate_all_bars=evaluate_all_bars)
        return {"event_forward_return_table": fwd, "binary_discrimination_table": disc, "all_bars_evaluation": all_bars}

    @staticmethod
    def _all_bars_for_events(result, bars_by_tf, *, seed: int, n_boot: int, evaluate_all_bars) -> Dict[str, Any]:
        """全 K 線驗證（U11 靈魂路徑）：把匯入事件集當訊號（事件 t₀ 根 score=1、其餘 0），固定分母跑 B2.5；
        manifest_config 全自事件欄導出（label_definition.window／direction／entry_price_semantic／timeframe 批內須單值）；
        prevalence_learn＝匯入事件正例率（case-control 揭露）。"""
        ev = result.events
        tfs = sorted(set(ev["timeframe"]))
        dirs = sorted(set(ev["direction"]))
        ents = sorted(set(ev["entry_price_semantic"]))
        ks = sorted({int(k) for k in ev["decision_offset_bars"]})   # CODEX-R2-P1-01：混合 k 不得取第一筆
        lds = {(d["window"]["horizon_bars"], d.get("label_return_mode", "close_to_close")) for d in ev["label_definition"]}
        if len(tfs) != 1 or len(dirs) != 1 or len(ents) != 1 or len(lds) != 1 or len(ks) != 1:
            return {"statistic_kind": "all_bars_evaluation", "capability_status": "not_computed",
                    "reason": "batch_not_single_valued",
                    "doc": ("全 K 線驗證需批內單一 timeframe/direction/entry_price_semantic/label_definition/decision_offset_bars"
                            f"（得 {len(tfs)}/{len(dirs)}/{len(ents)}/{len(lds)}/{len(ks)}）")}
        (horizon, mode), = lds
        if mode != "close_to_close":
            return {"statistic_kind": "all_bars_evaluation", "capability_status": "not_computed",
                    "reason": "label_return_mode_not_supported", "doc": f"evaluate_all_bars 標籤公式為 close_to_close；批為 {mode}"}
        tf, k = tfs[0], ks[0]
        bars = {s: bars_by_tf[s][tf] for s in sorted(set(ev["symbol"]))}
        # CODEX-R2-P1-01：`evaluate_all_bars` 於觸發根 i 取 `scores[ot[i-k]]`（**決策根**索引）⇒ 訊號須標在
        # 「t₀ 往前 k 根」之 open_time，而非 t₀ 本身；k=0 時兩者相同。缺該決策根 ⇒ 該事件不入訊號（loud 記數）。
        t0_by_symbol: Dict[str, set] = {}
        for s, t0 in zip(ev["symbol"], ev["t0"].astype("int64")):
            t0_by_symbol.setdefault(str(s), set()).add(int(t0))
        rows, n_signal, n_unmapped = [], 0, 0
        for s, b in bars.items():
            ot = b["open_time_ms"].astype("int64").to_numpy()
            pos = {int(t): i for i, t in enumerate(ot)}
            vals = np.zeros(len(ot), dtype=float)
            for t0 in sorted(t0_by_symbol.get(s, ())):
                i = pos.get(t0)
                if i is None or i - k < 0:
                    n_unmapped += 1
                    continue
                vals[i - k] = 1.0                       # 決策根
                n_signal += 1
            rows.append(pd.Series(vals, index=pd.MultiIndex.from_arrays([[s] * len(ot), ot])))
        scores = pd.concat(rows)
        cfg = {"horizon_bars": int(horizon), "label_threshold": 0.0, "direction": dirs[0],
               "decision_offset_bars": int(k), "score_threshold": 0.5, "top_q": 0.1,
               "prevalence_learn": float(ev["label"].mean()), "sample_design": "case_control",
               "seed": int(seed), "n_boot": int(n_boot), "label_id": "event_membership",
               "entry_price_semantic": ents[0], "timeframe": tf}
        rep = evaluate_all_bars(scores, bars, cfg, event_split_plan=result.split_plan, manifest=result.manifest)
        rep["rule"] = f"event_membership: score=1 於各事件之決策根（t₀ 往前 {k} 根 open），其餘 0"
        rep["label_threshold_note"] = ("threshold=0.0（signed 報酬 ≥0 ⇒ 1）；使用者標籤門檻不在事件欄位，"
                                       "故此表之 label 為 all-bars 基準語意，**非**使用者標註之正反例")
        rep["estimand_note"] = ("此表回答「若把這批事件當訊號、在全部 K 線上以固定分母評分會如何」——"
                                "不是模型預測力評估（事件本身即訊號，rule 無 out-of-sample 意義）")
        rep["signal_mapping"] = {"n_signal_bars": int(n_signal), "n_events_unmapped": int(n_unmapped),
                                 "decision_offset_bars": int(k), "indexed_at": "decision_bar_open_ms"}
        return rep

    def validate(
        self,
        records: Union[List[dict], pd.DataFrame],
        *,
        source_bytes: Optional[bytes] = None,
        batch_defaults: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[Optional[pd.DataFrame], List[Dict[str, Any]]]:
        """不 raise 之驗證：回 (正規化 df | None, failures)。failures 字面＝契約檔（唯一實作在 import_contract）。

        `batch_defaults`（Task 1.8）：已指定之維度視為已涵蓋，不再判異質列。

        🔴 本方法＝**使用者匯入路徑**之唯一入口（CSV／JSON 兩端點皆經此）
        ⇒ Task 1.8 之異質列拒收與 Task 1.3 之 `event_id` identity 契約在此開啟；
        `run()` 與 `generator.py` 走的是平台產生器路徑，兩者皆不開。
        """
        try:
            return validate_event_import(records, source_bytes=source_bytes, batch_defaults=batch_defaults,
                                         enforce_batch_homogeneity=True,
                                         enforce_canonical_event_id=True), []
        except ContractValidationError as exc:
            return None, list(exc.failures)

    def _prepare(
        self,
        records: Union[List[dict], pd.DataFrame],
        bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
        config: EventPipelineConfig,
        *,
        source_bytes: Optional[bytes],
        where: str,
    ):
        """validate → align → dedupe（切分**之前**的共用段；兩個 executor 共用同一實作，不各寫一份）。"""
        events = validate_event_import(records, source_bytes=source_bytes)
        tfs = tuple(config.timeframes) or tuple(sorted(set(events["timeframe"])))
        receipts, failures = align_events(events, bars_by_tf, AlignmentConfig(timeframes=tfs))
        if receipts.event_level.empty:
            raise ValueError(f"{where}: 全部事件對齊失敗 {n_dropped_by_reason(failures)}（loud）")

        scenarios = sorted(set(events["scenario"]))
        if len(scenarios) != 1:
            raise ValueError(f"{where}: 批內 scenario 混值 {scenarios}（去重 policy 須單一）")
        aligned = events[events["event_id"].isin(set(receipts.event_level["event_id"]))].reset_index(drop=True)
        manifest = build_event_manifest(
            receipts, DedupePolicyConfig(cluster_gap_ms=config.cluster_gap_ms, scenario=scenarios[0]), events=aligned,
        )
        return events, aligned, receipts, failures, manifest

    @staticmethod
    def _materialize(config, receipts, bars_by_tf, aligned):
        if config.feature_config is None:
            return None, None, None
        return materialize_features_at_decision(receipts, bars_by_tf, dict(config.feature_config), events=aligned)

    @staticmethod
    def _base_summary(events, receipts, failures, manifest, features, fhash, ffail) -> Dict[str, Any]:
        return {
            "n_input": int(len(events)),
            "n_aligned": int(len(receipts.event_level)),
            "n_align_failures": int(len(failures)),
            "align_failures_by_reason": n_dropped_by_reason(failures),
            "accounting_ok": int(len(events)) == int(len(receipts.event_level)) + int(len(failures)),
            "dedupe": {**manifest.summary, "policy": manifest.policy},
            "features": None if features is None else {
                "n_rows": int(len(features)), "n_cols": int(features.shape[1]),
                "n_failures": int(len(ffail)) if ffail is not None else 0, "feature_manifest_hash": fhash,
            },
        }

    def run(
        self,
        records: Union[List[dict], pd.DataFrame],
        bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
        config: EventPipelineConfig,
        *,
        source_bytes: Optional[bytes] = None,
        lookahead_gate: Optional[LookaheadGate] = None,
    ) -> EventPipelineResult:
        """全鏈（含切分）；匯入不合規 ⇒ raise ContractValidationError（fail-closed，不半套）。

        🔴 Task 1.12：`lookahead_gate` 判定封鎖時本方法**直接 raise**——切分是本路徑的固有步驟，
        不得以「警告後放行」降級。需要出表請改呼叫 `run_event_study_only()`。
        """
        assert_split_allowed(lookahead_gate, where="EventSamplePipeline.run")
        events, aligned, receipts, failures, manifest = self._prepare(
            records, bars_by_tf, config, source_bytes=source_bytes, where="EventSamplePipeline.run")
        plan = split_events(manifest, config.split, lookahead_gate=lookahead_gate)
        features, fhash, ffail = self._materialize(config, receipts, bars_by_tf, aligned)

        summary = self._base_summary(events, receipts, failures, manifest, features, fhash, ffail)
        summary.update({
            "split": {k: v for k, v in plan.summary.items() if k != "per_symbol_n"},
            "n_train": int((plan.assignments["split_label"] == "train").sum()) if not plan.assignments.empty else 0,
            "n_test": int((plan.assignments["split_label"] == "test").sum()) if not plan.assignments.empty else 0,
            "n_purged": int(len(plan.purged)),
        })
        if not summary["accounting_ok"]:
            raise RuntimeError("EventSamplePipeline.run: 對齊記帳守恆失敗")
        return EventPipelineResult(
            events=aligned, receipts=receipts, align_failures=failures, manifest=manifest, split_plan=plan,
            features=features, feature_manifest_hash=fhash, feature_failures=ffail, summary=summary,
        )

    def run_event_study_only(
        self,
        records: Union[List[dict], pd.DataFrame],
        bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
        config: EventPipelineConfig,
        *,
        source_bytes: Optional[bytes] = None,
    ) -> EventPipelineResult:
        """GAP-3 UX Task 1.12（D-7 之 L3）：**不切分**之 executor——深度不可證時的唯一可跑路徑。

        🔴 本方法**不呼叫** `split_events()`／`ic_feed`、不進訓練 ⇒ 無訓練即無洩漏。
        產出之 `split_plan` 為 `None`（**不是**空的假 plan——以空 plan 冒充未切分是具名之假綠形態）。
        `run()` 之 `split_events` 為無條件呼叫，故本批必須另立 executor，否則只能在
        「違反 L3」與「產不出表」之間二選一（SPEC Task 1.12 群集 E）。
        """
        events, aligned, receipts, failures, manifest = self._prepare(
            records, bars_by_tf, config, source_bytes=source_bytes, where="EventSamplePipeline.run_event_study_only")
        features, fhash, ffail = self._materialize(config, receipts, bars_by_tf, aligned)

        summary = self._base_summary(events, receipts, failures, manifest, features, fhash, ffail)
        summary.update({
            "split": None,
            "n_train": 0,
            "n_test": 0,
            "n_purged": 0,
            "execution_mode": "event_study_only",
        })
        if not summary["accounting_ok"]:
            raise RuntimeError("EventSamplePipeline.run_event_study_only: 對齊記帳守恆失敗")
        return EventPipelineResult(
            events=aligned, receipts=receipts, align_failures=failures, manifest=manifest, split_plan=None,
            features=features, feature_manifest_hash=fhash, feature_failures=ffail, summary=summary,
        )


__all__ = ["EventPipelineConfig", "EventPipelineResult", "EventSamplePipeline"]
