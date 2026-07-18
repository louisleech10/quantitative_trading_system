"""
Pattern Management Service - 模式管理服務

LA-2 B3：晉升 server 權威——create+PUT 從 task_result['oot_receipt'] verify 重建；
status='active' iff OOT receipt 通過；禁信前端 metadata/rules/metrics。

Author: AI Agent
Date: 2026-01-10
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from momentum.factories import (
    create_pattern,
    create_pattern_rule,
    create_pattern_storage,
    create_pattern_validator,
)
from api.core.logging import get_logger

logger = get_logger(__name__)


class PatternPromotionError(ValueError):
    """晉升失敗（缺 receipt / verify 失敗 / 偽造 client 欄位）。"""


class PatternManagementService:
    """模式管理服務"""

    def __init__(
        self,
        task_result_lookup: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    ) -> None:
        self.storage = create_pattern_storage()
        self.validator = create_pattern_validator()
        self.logger = logger
        # task_id → task_result dict（含 oot_receipt / decision_rules / ...）
        self._task_result_lookup = task_result_lookup

    def set_task_result_lookup(
        self, lookup: Callable[[str], Optional[Dict[str, Any]]]
    ) -> None:
        """注入 task result lookup（測試 / 啟動配線）。"""
        self._task_result_lookup = lookup

    def _lookup_task_result(self, task_id: str) -> Dict[str, Any]:
        if self._task_result_lookup is None:
            # 延遲綁定：嘗試 xgboost task + batch service
            result = self._default_task_lookup(task_id)
        else:
            result = self._task_result_lookup(task_id)
        if not isinstance(result, dict):
            raise PatternPromotionError(
                f"task_id not found or has no result: {task_id}"
            )
        return result

    @staticmethod
    def _default_task_lookup(task_id: str) -> Optional[Dict[str, Any]]:
        """從 xgboost task / batch service 查 task_result。"""
        try:
            from api.routes.pattern_analysis import xgboost_service

            task = xgboost_service.get_task_status(task_id)
            if isinstance(task, dict) and isinstance(task.get("result"), dict):
                return task["result"]
        except Exception:  # noqa: BLE001
            pass
        try:
            from api.services.xgboost_batch_service import get_xgboost_batch_service

            batch = get_xgboost_batch_service()
            task = batch.task_manager.get_task(task_id) if hasattr(batch, "task_manager") else None
            if isinstance(task, dict) and isinstance(task.get("result"), dict):
                return task["result"]
            # 某些 batch 用 get_task_status
            if hasattr(batch, "get_task_status"):
                st = batch.get_task_status(task_id)
                if isinstance(st, dict) and isinstance(st.get("result"), dict):
                    return st["result"]
        except Exception:  # noqa: BLE001
            pass
        return None

    @staticmethod
    def _coerce_split_plan(obj: Any, *, where: str) -> Any:
        """SplitPlan 或 dict → SplitPlan（fail-closed）。"""
        from momentum.core.contracts import SplitPlan

        if isinstance(obj, SplitPlan):
            return obj
        if not isinstance(obj, dict):
            raise PatternPromotionError(f"missing_or_invalid_{where}")
        try:
            tb = obj.get("time_bounds")
            if isinstance(tb, (list, tuple)) and len(tb) == 2:
                time_bounds = (tb[0], tb[1])
            else:
                time_bounds = (None, None)
            return SplitPlan(
                split_label=obj["split_label"],
                index_kind=obj["index_kind"],
                row_index=np.asarray(obj["row_index"], dtype=int),
                time_bounds=time_bounds,
                purge_gap=int(obj.get("purge_gap", 0)),
                embargo=int(obj.get("embargo", 0)),
                purge_semantic=obj.get("purge_semantic", "rows"),
                expected_freq=obj.get("expected_freq"),
                base_universe_hash=str(obj.get("base_universe_hash") or ""),
                symbol=obj.get("symbol"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PatternPromotionError(f"invalid_{where}: {exc}") from exc

    @staticmethod
    def _coerce_model_artifact(obj: Any) -> bytes:
        """model_artifact → bytes（fail-closed if absent）。"""
        if obj is None:
            raise PatternPromotionError("missing_model_artifact")
        if isinstance(obj, (bytes, bytearray)):
            return bytes(obj)
        if isinstance(obj, str):
            # producers may base64-encode; try raw utf-8 fallback for short test artifacts
            try:
                import base64

                return base64.b64decode(obj, validate=True)
            except Exception:  # noqa: BLE001
                return obj.encode("utf-8")
        raise PatternPromotionError("invalid_model_artifact_type")

    def _verify_oot_and_rebuild(
        self, task_result: Dict[str, Any]
    ) -> tuple[bool, List[Dict], Dict[str, float], Dict[str, float], str, Dict]:
        """從 task_result 驗證 OOT receipt 並重建 rules/performance/importance。

        LA-2 B3-F1：晉升 active **必須** train_plan + eval_plan + model_artifact
        跑 ``verify_oot_receipt``；缺任一 → fail-closed 非 active（無 issuer+digest 旁路）。

        Returns:
            (is_active, rules_dict_list, importance, performance, case_id, metadata)
        """
        from momentum.core.contracts import (
            OotReceipt,
            ReceiptVerificationError,
            verify_oot_receipt,
        )

        oot_env = task_result.get("oot_receipt")
        is_active = False
        blocked_reason = "missing_or_invalid_oot_receipt"
        if oot_env is not None:
            try:
                if not isinstance(oot_env, dict) or oot_env.get("receipt_kind") != "oot":
                    raise PatternPromotionError("oot_receipt envelope invalid")
                fields = oot_env.get("fields") or {}
                receipt = OotReceipt(**fields)
                # B3-F1：三份 provenance 缺一不可；禁 issuer+digest fallback
                train_raw = task_result.get("train_plan")
                eval_raw = task_result.get("eval_plan")
                artifact_raw = task_result.get("model_artifact")
                if train_raw is None or eval_raw is None or artifact_raw is None:
                    raise PatternPromotionError(
                        "missing_oot_provenance: require train_plan+eval_plan+model_artifact"
                    )
                train_plan = self._coerce_split_plan(train_raw, where="train_plan")
                eval_plan = self._coerce_split_plan(eval_raw, where="eval_plan")
                model_artifact = self._coerce_model_artifact(artifact_raw)
                verify_oot_receipt(
                    receipt,
                    train_plan,
                    eval_plan,
                    horizon=int(receipt.horizon),
                    model_artifact=model_artifact,
                    envelope=oot_env,
                )
                is_active = True
            except (ReceiptVerificationError, TypeError, KeyError, PatternPromotionError) as exc:
                self.logger.warning("OOT receipt verify failed: %s", exc)
                is_active = False
                blocked_reason = f"oot_verify_failed:{exc}"
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("OOT receipt verify error: %s", exc)
                is_active = False
                blocked_reason = f"oot_verify_error:{exc}"

        # B3-F6：active 須每條 promotion rule 有 finite OOT lift（缺/部分缺→非 active）
        decision_rules = task_result.get("decision_rules") or []
        if is_active:
            finite_oot: List[float] = []
            n_promotion_rules = 0
            for rule in decision_rules:
                if not isinstance(rule, dict):
                    continue
                fcs = rule.get("feature_conditions") or []
                if not fcs:
                    continue
                n_promotion_rules += 1
                oot_lift = rule.get("oot_lift")
                try:
                    lift_f = float(oot_lift) if oot_lift is not None else float("nan")
                except (TypeError, ValueError):
                    lift_f = float("nan")
                if not math.isfinite(lift_f):
                    is_active = False
                    blocked_reason = "missing_or_nonfinite_oot_lift"
                    break
                finite_oot.append(lift_f)
            if is_active and n_promotion_rules == 0:
                is_active = False
                blocked_reason = "no_promotion_rules_with_oot_lift"

        # server 重建 rules（禁 client）
        rules: List[Dict] = []
        for rule in decision_rules:
            if not isinstance(rule, dict):
                continue
            fcs = rule.get("feature_conditions") or []
            if not fcs:
                # 單 feature 退化：從 condition 字串無法可靠解析時 skip
                continue
            # 鎖 AND / 順序 / 空集拒
            first = fcs[0]
            feature = first.get("feature") if isinstance(first, dict) else first[0]
            operator = first.get("operator") if isinstance(first, dict) else first[1]
            # threshold = condition 分位值（非 confidence）
            threshold = (
                first.get("threshold") if isinstance(first, dict) else first[2]
            )
            # 晉升 OOT lift 來源斷言：active 時必須用 oot_lift
            if is_active:
                lift_src = rule.get("oot_lift")
            else:
                lift_src = rule.get("oot_lift", rule.get("lift"))
            desc = rule.get("condition") or f"{feature} {operator} {threshold}"
            rules.append(
                {
                    "feature": str(feature),
                    "operator": str(operator),
                    "threshold": float(threshold),
                    "description": str(desc),
                    "feature_conditions": fcs,
                    "connective": "AND",
                    "lift": lift_src,
                    "confidence": rule.get("confidence"),
                    "support": rule.get("support"),
                }
            )

        # importance / performance 自 task_result 推導
        importance: Dict[str, float] = {}
        fi = task_result.get("feature_importance") or []
        if isinstance(fi, list):
            for item in fi:
                if isinstance(item, dict) and "feature" in item:
                    importance[str(item["feature"])] = float(
                        item.get("importance", 0.0)
                    )
        elif isinstance(fi, dict):
            importance = {str(k): float(v) for k, v in fi.items()}

        mp = task_result.get("model_performance") or {}
        if isinstance(mp, dict) and "value" in mp and isinstance(mp["value"], dict):
            # scoped envelope
            performance = {
                k: float(v) if isinstance(v, (int, float)) else v
                for k, v in mp["value"].items()
                if isinstance(v, (int, float))
            }
            # 附 eval_scope for in_sample_train_auc
            scopes = mp.get("eval_scope") or {}
            if "in_sample_train_auc" in performance:
                performance["in_sample_train_auc_eval_scope"] = scopes.get(
                    "in_sample_train_auc", "in_sample_research_only"
                )
        elif isinstance(mp, dict):
            performance = {
                k: float(v)
                for k, v in mp.items()
                if isinstance(v, (int, float))
            }
        else:
            performance = {}

        # OOT lift 進 performance（晉升來源；B3-F6 產 oot_lift_source）
        if is_active and rules:
            oot_lifts = []
            for r in rules:
                lv = r.get("lift")
                try:
                    lf = float(lv) if lv is not None else float("nan")
                except (TypeError, ValueError):
                    lf = float("nan")
                if math.isfinite(lf):
                    oot_lifts.append(lf)
            if oot_lifts and len(oot_lifts) == len(rules):
                performance["oot_lift_mean"] = float(sum(oot_lifts) / len(oot_lifts))
                performance["oot_lift_source"] = "oot"
            else:
                is_active = False
                blocked_reason = "missing_or_nonfinite_oot_lift"

        case_id = str(task_result.get("case_id") or task_result.get("symbol") or "unknown")
        metadata = {
            "in_sample_rules": not is_active,
            "promotion_source": "server_oot_receipt",
            "server_rebuilt": True,
        }
        if not is_active:
            metadata["promotion_blocked_reason"] = blocked_reason

        return is_active, rules, importance, performance, case_id, metadata

    def create_pattern(
        self,
        name: str,
        description: str,
        task_id: str,
        tags: Optional[List[str]] = None,
        *,
        # 以下參數若被傳入 → 視為偽造 client 欄位 → 拒
        rules: Any = None,
        case_id: Any = None,
        xgboost_importance: Any = None,
        performance_metrics: Any = None,
        metadata: Any = None,
        status: Any = None,
    ) -> Dict:
        """建立新模式（server 從 task_id→oot_receipt 重建）。"""
        # 拒 client 偽造
        for banned, val in (
            ("rules", rules),
            ("case_id", case_id),
            ("xgboost_importance", xgboost_importance),
            ("performance_metrics", performance_metrics),
            ("metadata", metadata),
            ("status", status),
        ):
            if val is not None:
                return {
                    "success": False,
                    "error": f"client field '{banned}' rejected (server authority)",
                }

        pattern_id = (
            f"PAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        self.logger.info("開始建立模式 - ID: %s task_id=%s", pattern_id, task_id)

        try:
            task_result = self._lookup_task_result(task_id)
            is_active, rules_dicts, importance, performance, case_id_s, meta = (
                self._verify_oot_and_rebuild(task_result)
            )
            if not rules_dicts:
                return {
                    "success": False,
                    "error": "no decision_rules rebuildable from task_result",
                }

            pattern_rules = []
            for rule in rules_dicts:
                pattern_rules.append(
                    create_pattern_rule(
                        feature=rule["feature"],
                        operator=rule["operator"],
                        threshold=rule["threshold"],
                        description=rule.get("description") or "",
                    )
                )

            now = datetime.now().isoformat()
            status_s = "active" if is_active else "testing"
            meta = dict(meta)
            meta["source_task_id"] = task_id

            pattern = create_pattern(
                pattern_id=pattern_id,
                name=name,
                description=description,
                rules=pattern_rules,
                case_id=case_id_s,
                xgboost_importance=importance,
                performance_metrics=performance,
                created_at=now,
                updated_at=now,
                status=status_s,
                tags=tags or [],
                metadata=meta,
            )

            is_valid, errors = self.validator.validate_pattern(pattern)
            if not is_valid:
                self.logger.error("模式驗證失敗 - ID: %s, 錯誤: %s", pattern_id, errors)
                return {
                    "success": False,
                    "error": "模式驗證失敗",
                    "validation_errors": errors,
                }

            file_path = self.storage.save_pattern_to_json(pattern)
            self.logger.info("模式建立成功 - ID: %s status=%s", pattern_id, status_s)
            return {
                "success": True,
                "pattern_id": pattern_id,
                "pattern": pattern.to_dict(),
                "file_path": file_path,
                "message": "模式建立成功",
                "status": status_s,
            }

        except PatternPromotionError as e:
            self.logger.error("晉升失敗: %s", e)
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error("建立模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def get_pattern(self, pattern_id: str) -> Dict:
        try:
            if not self.storage.pattern_exists(pattern_id):
                return {"success": False, "error": f"模式不存在: {pattern_id}"}
            pattern = self.storage.load_pattern_from_json(pattern_id)
            return {"success": True, "pattern": pattern.to_dict()}
        except Exception as e:
            self.logger.error("獲取模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def list_patterns(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        case_id: Optional[str] = None,
    ) -> Dict:
        try:
            patterns = self.storage.query_patterns(
                status=status, tags=tags, case_id=case_id
            )
            pattern_list = [p.to_dict() for p in patterns]
            self.logger.info("列出模式 - 共 %d 個", len(pattern_list))
            return {
                "success": True,
                "count": len(pattern_list),
                "patterns": pattern_list,
            }
        except Exception as e:
            self.logger.error("列出模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def update_pattern(
        self,
        pattern_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        *,
        # 禁 client 直改
        status: Any = None,
        metadata: Any = None,
    ) -> Dict:
        """更新模式（status/metadata 禁 client；可帶 task_id re-verify）。"""
        if status is not None:
            return {
                "success": False,
                "error": "client field 'status' rejected (server authority)",
            }
        if metadata is not None:
            return {
                "success": False,
                "error": "client field 'metadata' rejected (server authority)",
            }

        try:
            if not self.storage.pattern_exists(pattern_id):
                return {"success": False, "error": f"模式不存在: {pattern_id}"}

            pattern = self.storage.load_pattern_from_json(pattern_id)

            if name is not None:
                pattern.name = name
            if description is not None:
                pattern.description = description
            if tags is not None:
                pattern.tags = tags

            # re-verify OOT if task_id provided
            if task_id is not None:
                task_result = self._lookup_task_result(task_id)
                is_active, rules_dicts, importance, performance, case_id_s, meta = (
                    self._verify_oot_and_rebuild(task_result)
                )
                if rules_dicts:
                    pattern.rules = [
                        create_pattern_rule(
                            feature=r["feature"],
                            operator=r["operator"],
                            threshold=r["threshold"],
                            description=r.get("description") or "",
                        )
                        for r in rules_dicts
                    ]
                pattern.xgboost_importance = importance
                pattern.performance_metrics = performance
                pattern.case_id = case_id_s
                meta = dict(meta)
                meta["source_task_id"] = task_id
                pattern.metadata = meta
                pattern.status = "active" if is_active else "testing"
            # 無 task_id：不得由 client 推 active；維持現狀除非已是 active 且再驗證
            # （不自動升級）

            pattern.updated_at = datetime.now().isoformat()

            is_valid, errors = self.validator.validate_pattern(pattern)
            if not is_valid:
                return {
                    "success": False,
                    "error": "模式驗證失敗",
                    "validation_errors": errors,
                }

            self.storage.save_pattern_to_json(pattern)
            self.logger.info("模式更新成功 - ID: %s", pattern_id)
            return {
                "success": True,
                "pattern": pattern.to_dict(),
                "message": "模式更新成功",
            }

        except PatternPromotionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error("更新模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_pattern(self, pattern_id: str) -> Dict:
        try:
            if not self.storage.pattern_exists(pattern_id):
                return {"success": False, "error": f"模式不存在: {pattern_id}"}
            self.storage.delete_pattern(pattern_id)
            return {"success": True, "message": f"模式已刪除: {pattern_id}"}
        except Exception as e:
            self.logger.error("刪除模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_all_patterns(self) -> Dict:
        """刪除所有已存模式（B3-F7：route DELETE /batch/delete-all）。"""
        try:
            files = self.storage.list_pattern_files()
            deleted = 0
            errors: List[str] = []
            for info in files:
                pid = str(info.get("pattern_id") or "")
                if not pid:
                    continue
                ok = self.storage.delete_pattern(pid)
                if ok:
                    deleted += 1
                else:
                    errors.append(pid)
            return {
                "success": True,
                "deleted": deleted,
                "errors": errors,
                "message": f"deleted {deleted} patterns",
            }
        except Exception as e:
            self.logger.error("刪除所有模式失敗: %s", e, exc_info=True)
            return {"success": False, "error": str(e)}

    def get_pattern_summary(self, pattern_id: str) -> Dict:
        try:
            result = self.get_pattern(pattern_id)
            if not result.get("success"):
                return result
            p = result["pattern"]
            rules = p.get("rules") or []
            cond = " AND ".join(
                f"{r.get('feature')} {r.get('operator')} {r.get('threshold')}"
                for r in rules
            )
            return {
                "success": True,
                "summary": {
                    "pattern_id": p["pattern_id"],
                    "name": p["name"],
                    "description": p["description"],
                    "rule_count": len(rules),
                    "rule_condition": cond,
                    "case_id": p.get("case_id"),
                    "performance_metrics": p.get("performance_metrics") or {},
                    "status": p.get("status"),
                    "tags": p.get("tags") or [],
                    "created_at": p.get("created_at"),
                    "updated_at": p.get("updated_at"),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_statistics(self) -> Dict:
        try:
            patterns = self.storage.query_patterns()
            total = len(patterns)
            by_status = {"active": 0, "archived": 0, "testing": 0}
            tag_counts: Dict[str, int] = {}
            rule_total = 0
            for p in patterns:
                st = getattr(p, "status", None) or (p.get("status") if isinstance(p, dict) else "testing")
                if st in by_status:
                    by_status[st] += 1
                rules = getattr(p, "rules", None) or (
                    p.get("rules") if isinstance(p, dict) else []
                )
                rule_total += len(rules or [])
                tags = getattr(p, "tags", None) or (
                    p.get("tags") if isinstance(p, dict) else []
                )
                for t in tags or []:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
            return {
                "success": True,
                "total": total,
                "active": by_status["active"],
                "archived": by_status["archived"],
                "testing": by_status["testing"],
                "avg_rules_per_pattern": (rule_total / total) if total else 0.0,
                "top_tags": top_tags,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
