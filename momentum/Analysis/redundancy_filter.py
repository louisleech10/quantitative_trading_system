"""Redundancy filter utilities for IC analysis."""

from __future__ import annotations

from typing import Any, Optional, Protocol

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.linear_model import LinearRegression

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class IRedundancyFilter(Protocol):
    """Redundancy filter protocol (module-local)."""

    def filter(
        self,
        features_df: pd.DataFrame,
        ic_scores: dict,
        method: str = "greedy",
    ) -> tuple[pd.DataFrame, dict]:
        ...

    def compute_correlation_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        ...

    def greedy_dedup(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        threshold: float = 0.7,
        tiebreaker: str = "icir",
    ) -> list[str]:
        ...

    def hierarchical_clustering(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        linkage_method: str = "average",
    ) -> list[str]:
        ...

    def vif_filter(
        self,
        features_df: pd.DataFrame,
        max_vif: float = 10.0,
        ic_scores: Optional[dict] = None,
    ) -> list[str]:
        ...

    def compute_diversification_metrics(
        self,
        selected_features: list[str],
        corr_matrix: pd.DataFrame,
        metadata: dict,
    ) -> dict:
        ...

    def apply_diversification_constraint(
        self,
        features_df: pd.DataFrame,
        selected: list[str],
        candidates: list[str],
        ic_scores: dict,
        metadata: dict,
    ) -> tuple[list[str], dict]:
        ...


class RedundancyFilter:
    """Stage 6: 冗餘剔除 — 相關性矩陣 + 階層聚類 + VIF。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._method = self._config.get("method", "greedy")
        self._corr_threshold = float(self._config.get("correlation_threshold", 0.7))
        self._tiebreaker = self._config.get("tiebreaker", "icir")
        hierarchical = self._config.get("hierarchical", {}) or {}
        self._linkage_method = hierarchical.get("linkage_method", "average")
        vif_cfg = self._config.get("vif", {}) or {}
        self._max_vif = float(vif_cfg.get("max_vif", 10.0))
        div_cfg = self._config.get("diversification", {}) or {}
        self._div_enabled = bool(div_cfg.get("enabled", False))
        self._div_min_categories = int(div_cfg.get("min_categories", 3))
        self._div_min_data_sources = int(div_cfg.get("min_data_sources", 2))
        self._div_max_same_category_pct = float(div_cfg.get("max_same_category_pct", 0.4))

    @property
    def diversification_enabled(self) -> bool:
        """ICPERF Task 0.4 ㊲：多元化約束是否開啟（關 ⇒ 第 6 段與改前相同）。"""
        return self._div_enabled

    def diversification_settings(self) -> dict:
        """多元化約束之有效設定（enabled 與三數值）。"""
        return {
            "enabled": self._div_enabled,
            "min_categories": self._div_min_categories,
            "min_data_sources": self._div_min_data_sources,
            "max_same_category_pct": self._div_max_same_category_pct,
        }

    def filter(
        self,
        features_df: pd.DataFrame,
        ic_scores: dict,
        method: str = "greedy",
    ) -> tuple[pd.DataFrame, dict]:
        """冗餘剔除主入口。"""

        if features_df is None:
            raise ValueError("features_df is required")
        if features_df.empty:
            return features_df.copy(), {
                "method": method,
                "input_features": 0,
                "output_features": 0,
                "removed_features": [],
            }

        method = method or self._method
        corr_matrix: Optional[pd.DataFrame] = None

        if method in {"greedy", "hierarchical"}:
            corr_matrix = self.compute_correlation_matrix(features_df)
            if method == "greedy":
                selected = self.greedy_dedup(
                    corr_matrix,
                    ic_scores,
                    threshold=self._corr_threshold,
                    tiebreaker=self._tiebreaker,
                )
            else:
                selected = self.hierarchical_clustering(
                    corr_matrix,
                    ic_scores,
                    linkage_method=self._linkage_method,
                )
        elif method == "vif":
            selected = self.vif_filter(
                features_df,
                max_vif=self._max_vif,
                ic_scores=ic_scores,
            )
        else:
            raise ValueError(f"unsupported redundancy method: {method}")

        selected = [name for name in features_df.columns if name in selected]
        removed = [name for name in features_df.columns if name not in selected]
        filtered_df = features_df[selected].copy()

        if corr_matrix is None:
            corr_matrix = (
                self.compute_correlation_matrix(filtered_df)
                if len(selected) > 1
                else pd.DataFrame(index=selected, columns=selected, data=1.0)
            )

        log = {
            "method": method,
            "input_features": int(len(features_df.columns)),
            "output_features": int(len(selected)),
            "removed_features": removed,
            "correlation_threshold": self._corr_threshold,
        }

        logger.info(
            "Redundancy filter completed: method=%s input=%s output=%s",
            method,
            len(features_df.columns),
            len(selected),
        )

        return filtered_df, log

    def compute_correlation_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """計算特徵間 Pearson 相關性矩陣。"""

        if features_df.empty:
            return pd.DataFrame()

        numeric_df = features_df.apply(pd.to_numeric, errors="coerce")
        values = numeric_df.to_numpy(dtype=float)
        if np.isnan(values).any():
            return numeric_df.corr(method="pearson")

        mean = values.mean(axis=0)
        values = values - mean
        std = values.std(axis=0, ddof=1)
        std[std == 0] = np.nan
        values = values / std
        corr = (values.T @ values) / (values.shape[0] - 1)
        corr = np.clip(corr, -1.0, 1.0)
        return pd.DataFrame(corr, index=numeric_df.columns, columns=numeric_df.columns)

    def greedy_dedup(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        threshold: float = 0.7,
        tiebreaker: str = "icir",
    ) -> list[str]:
        """貪婪去重：按 ICIR 排序，逐一檢查相關性。"""

        if corr_matrix.empty:
            return []

        features = list(corr_matrix.columns)
        ordered = sorted(
            features,
            key=lambda name: self._score_value(ic_scores, name, tiebreaker),
            reverse=True,
        )

        selected: list[str] = []
        for feature in ordered:
            if not selected:
                selected.append(feature)
                continue

            correlations = corr_matrix.loc[feature, selected].abs()
            if correlations.isna().all():
                selected.append(feature)
                continue

            if (correlations > threshold).any():
                continue

            selected.append(feature)

        return selected

    def hierarchical_clustering(
        self,
        corr_matrix: pd.DataFrame,
        ic_scores: dict,
        linkage_method: str = "average",
    ) -> list[str]:
        """階層聚類：每個 cluster 保留 ICIR 最高的特徵。"""

        if corr_matrix.empty:
            return []

        features = list(corr_matrix.columns)
        if len(features) <= 1:
            return features

        abs_corr = corr_matrix.abs().fillna(0.0)
        distance = 1.0 - abs_corr
        np.fill_diagonal(distance.values, 0.0)

        condensed = squareform(distance.values, checks=False)
        linkage_matrix = linkage(condensed, method=linkage_method)
        threshold = 1.0 - float(self._corr_threshold)
        clusters = fcluster(linkage_matrix, t=threshold, criterion="distance")

        cluster_map: dict[int, list[str]] = {}
        for feature, cluster_id in zip(features, clusters):
            cluster_map.setdefault(int(cluster_id), []).append(feature)

        selected: list[str] = []
        for members in cluster_map.values():
            best = max(
                members,
                key=lambda name: self._score_value(ic_scores, name, self._tiebreaker),
            )
            selected.append(best)

        return selected

    def vif_filter(
        self,
        features_df: pd.DataFrame,
        max_vif: float = 10.0,
        ic_scores: Optional[dict] = None,
    ) -> list[str]:
        """VIF 篩選：逐步移除 VIF > threshold 的特徵。"""

        if features_df.empty:
            return []

        features = list(features_df.columns)
        data = features_df[features].apply(pd.to_numeric, errors="coerce").dropna()
        if data.empty or data.shape[1] <= 1:
            return features

        while True:
            vifs = self._compute_vif_scores(data)
            if not vifs:
                break

            max_feature, max_value = max(vifs.items(), key=lambda item: item[1])
            if max_value <= max_vif or len(features) <= 1:
                return features

            candidates = [name for name, value in vifs.items() if value == max_value]
            if len(candidates) > 1 and ic_scores:
                max_feature = min(
                    candidates,
                    key=lambda name: self._score_value(ic_scores, name, self._tiebreaker),
                )

            features.remove(max_feature)
            data = data[features]
            if data.shape[1] <= 1:
                break

        return features

    def compute_diversification_metrics(
        self,
        selected_features: list[str],
        corr_matrix: pd.DataFrame,
        metadata: dict,
    ) -> dict:
        """多元化指標。"""

        if not selected_features:
            return {
                "avg_abs_correlation": float("nan"),
                "max_correlation": float("nan"),
                "effective_independent_features": 0.0,
                "category_coverage": 0.0,
                "data_source_coverage": 0.0,
                "layer_coverage": 0.0,
            }

        if corr_matrix.empty or not set(selected_features).issubset(
            set(corr_matrix.index)
        ):
            sub_corr = pd.DataFrame(
                np.eye(len(selected_features)),
                index=selected_features,
                columns=selected_features,
            )
        else:
            sub_corr = corr_matrix.loc[selected_features, selected_features]
        abs_corr = sub_corr.abs().fillna(0.0)
        upper = abs_corr.where(
            np.triu(np.ones(abs_corr.shape), k=1).astype(bool)
        )
        values = upper.stack().to_numpy()
        if values.size == 0:
            avg_abs = 0.0
            max_corr = 0.0
        else:
            avg_abs = float(np.mean(values))
            max_corr = float(np.max(values))

        n_features = len(selected_features)
        if n_features <= 1:
            effective = 1.0
        else:
            effective = float(n_features / (1.0 + avg_abs * (n_features - 1)))

        category_coverage = self._compute_coverage(
            metadata, selected_features, "category"
        )
        data_source_coverage = self._compute_coverage(
            metadata, selected_features, "data_source"
        )
        layer_coverage = self._compute_coverage(metadata, selected_features, "layer")

        return {
            "avg_abs_correlation": avg_abs,
            "max_correlation": max_corr,
            "effective_independent_features": effective,
            "category_coverage": category_coverage,
            "data_source_coverage": data_source_coverage,
            "layer_coverage": layer_coverage,
        }

    # ------------------------------------------------------------------ ICPERF Task 0.4 ㊲ 多元化約束
    _DIV_EPS = 1e-9

    def apply_diversification_constraint(
        self,
        features_df: pd.DataFrame,
        selected: list[str],
        candidates: list[str],
        ic_scores: dict,
        metadata: dict,
    ) -> tuple[list[str], dict]:
        """第 6 段多元化約束（ICPERF Task 0.4 ㊲）：冗餘剔除後之倖存集合 S 須滿足
        ①相異類別數 ≥ `min_categories` ②相異資料來源數 ≥ `min_data_sources`
        ③任一類別之倖存數 ≤ `max_same_category_pct` ×（類別已知之倖存數）。

        輸入：`features_df`＝第 6 段所用之列（切分成立時為測試段）；`selected`＝冗餘剔除之倖存；`candidates`＝通過第 5 段
        門檻之全部特徵（順序＝通過名單順序）；`ic_scores`＝冗餘所用之分數（同 tiebreaker）；`metadata`＝逐特徵 metadata。

        規則（依序；每一步皆確定性）：
        - 已知值：metadata 項為 dict、`metadata_source` 不為 `missing`、該欄不為 None；否則該特徵不計入任何類別或來源
          （③之分母亦不計），並記數於 `metadata_missing`。
        - 排序鍵：同冗餘之分數（非有限 ⇒ 最低），同分依通過名單順序。「合格候選」＝在 `candidates` 中、不在 S、未曾被本約束
          剔除，且與當下 S 之每一成員 |Pearson（兩者皆有限之列）| ≤ `correlation_threshold`（相關 NaN 視為不冗餘）——與
          冗餘剔除同一門檻，補入不得重新引入冗餘。
        - 步驟 1（①）：相異類別數不足時，自合格候選中取「類別已知且為 S 所無」之最高排序者補入，重複至滿足；無此候選 ⇒
          未滿足，原因 `candidates_redundant`（有新類別候選但皆冗餘）或 `no_candidate_with_new_value`。
        - 步驟 2（②）：同步驟 1，對資料來源。
        - 步驟 3（③）：違反時取倖存數最多之類別 k（同數取名稱最小），於 k 之成員中由排序最低者起，取第一個「移除後相異
          類別數 ≥ min(①下限, 移除前) 且相異來源數 ≥ min(②下限, 移除前)」者 r（全受保護 ⇒ 未滿足 `coverage_protected`）；
          先嘗試換入：最高排序之合格候選 e（相對 S∖{r}），其類別已知、≠ k、且換入後該類別數 ≤ 門檻 ⇒ 以 e 換 r（集合大小
          不變）；無 e 時，若相異類別數 × 比例 < 1（即使每類只留一個仍超過）⇒ 未滿足 `insufficient_categories`、不剔除；
          否則剔除 r。重複至滿足。
        - 終止：每次換入／剔除皆使一個特徵永久離開，候選有限。

        業界對齊：於分數排序下加群組（類別）上限之貪婪選取＝分割擬陣（partition matroid）上之貪婪，於群組上限下為總分最大
        （Edmonds 1971, "Matroids and the greedy algorithm"）；群組下限以補入最高分者滿足，同組合建構中之產業／風格曝險上下限
        （Grinold & Kahn, *Active Portfolio Management*, 2nd ed., ch. 14 portfolio construction constraints）。

        回 (最終倖存〔依 `candidates` 順序〕, 記錄)。`enabled` 為 False 時呼叫端不應呼叫（回原集合與 `{"enabled": False}`）。
        """

        settings = self.diversification_settings()
        if not self._div_enabled:
            return list(selected), {"enabled": False}
        min_c = self._div_min_categories
        min_s = self._div_min_data_sources
        pct = self._div_max_same_category_pct
        eps = self._DIV_EPS
        metadata = metadata or {}
        order = list(candidates)
        position = {name: i for i, name in enumerate(order)}
        score = {
            name: self._score_value(ic_scores, name, self._tiebreaker) for name in order
        }
        rank = sorted(order, key=lambda name: (-score[name], position[name]))
        rank_pos = {name: i for i, name in enumerate(rank)}
        selected_set = set(selected)
        members = [name for name in rank if name in selected_set]
        gone: set[str] = set()
        added: list[dict] = []
        removed: list[dict] = []
        unmet: dict[str, str] = {}
        corr_cache: dict[tuple[str, str], float] = {}
        arrays: dict[str, np.ndarray] = {}

        def known(name: str, key: str) -> Optional[str]:
            info = metadata.get(name)
            if not isinstance(info, dict) or info.get("metadata_source") == "missing":
                return None
            value = info.get(key)
            return None if value is None else str(value)

        def values(names: list[str], key: str) -> list[str]:
            return [v for v in (known(n, key) for n in names) if v is not None]

        def column(name: str) -> np.ndarray:
            arr = arrays.get(name)
            if arr is None:
                arr = pd.to_numeric(features_df[name], errors="coerce").to_numpy(dtype=float)
                arrays[name] = arr
            return arr

        def abs_corr(a: str, b: str) -> float:
            pair = (a, b) if a <= b else (b, a)
            cached = corr_cache.get(pair)
            if cached is not None:
                return cached
            x, y = column(a), column(b)
            mask = np.isfinite(x) & np.isfinite(y)
            value = float("nan")
            if int(mask.sum()) >= 2:
                xm = x[mask] - x[mask].mean()
                ym = y[mask] - y[mask].mean()
                den = float(np.sqrt(np.dot(xm, xm) * np.dot(ym, ym)))
                if den > 0.0:
                    value = abs(float(np.dot(xm, ym) / den))
            corr_cache[pair] = value
            return value

        def redundant(name: str, against: list[str]) -> bool:
            for other in against:
                value = abs_corr(name, other)
                if np.isfinite(value) and value > self._corr_threshold:
                    return True
            return False

        def admissible(before: list[str], after: list[str]) -> bool:
            cats_b, cats_a = len(set(values(before, "category"))), len(set(values(after, "category")))
            srcs_b, srcs_a = len(set(values(before, "data_source"))), len(set(values(after, "data_source")))
            return cats_a >= min(min_c, cats_b) and srcs_a >= min(min_s, srcs_b)

        def entry(name: str, condition: str, **extra: Any) -> dict:
            value = score[name]
            return {
                "name": name,
                "category": known(name, "category"),
                "data_source": known(name, "data_source"),
                "score": value if np.isfinite(value) else None,
                "condition": condition,
                **extra,
            }

        def summary(names: list[str]) -> dict:
            cats = values(names, "category")
            srcs = values(names, "data_source")
            cat_counts: dict[str, int] = {}
            for c in cats:
                cat_counts[c] = cat_counts.get(c, 0) + 1
            src_counts: dict[str, int] = {}
            for s in srcs:
                src_counts[s] = src_counts.get(s, 0) + 1
            return {
                "n_features": len(names),
                "n_categories": len(cat_counts),
                "n_data_sources": len(src_counts),
                "max_category_share": (max(cat_counts.values()) / len(cats)) if cats else None,
                "category_counts": dict(sorted(cat_counts.items())),
                "data_source_counts": dict(sorted(src_counts.items())),
            }

        def missing_count(names: list[str]) -> int:
            return sum(
                1 for n in names
                if not isinstance(metadata.get(n), dict) or metadata[n].get("metadata_source") == "missing"
            )

        before = list(members)
        for condition, key, need in (
            ("min_categories", "category", min_c),
            ("min_data_sources", "data_source", min_s),
        ):
            while len(set(values(members, key))) < need:
                have = set(values(members, key))
                pool = [
                    name for name in rank
                    if name not in members and name not in gone
                    and known(name, key) is not None and known(name, key) not in have
                ]
                pick = next((name for name in pool if not redundant(name, members)), None)
                if pick is None:
                    unmet[condition] = "candidates_redundant" if pool else "no_candidate_with_new_value"
                    break
                members.append(pick)
                added.append(entry(pick, condition))

        while True:
            cats = values(members, "category")
            n_known = len(cats)
            counts: dict[str, int] = {}
            for c in cats:
                counts[c] = counts.get(c, 0) + 1
            if n_known == 0 or max(counts.values()) <= pct * n_known + eps:
                break
            top = max(counts.values())
            k = sorted(c for c, v in counts.items() if v == top)[0]
            in_rank = sorted(members, key=lambda name: rank_pos[name])
            victims = [name for name in reversed(in_rank) if known(name, "category") == k]
            r = next(
                (name for name in victims if admissible(members, [m for m in members if m != name])),
                None,
            )
            if r is None:
                unmet["max_same_category_pct"] = "coverage_protected"
                break
            rest = [m for m in members if m != r]
            swap = None
            for name in rank:
                if name in members or name in gone:
                    continue
                cat = known(name, "category")
                if cat is None or cat == k or counts.get(cat, 0) + 1 > pct * n_known + eps:
                    continue
                if redundant(name, rest):
                    continue
                swap = name
                break
            if swap is not None:
                members = rest + [swap]
                gone.add(r)
                removed.append(entry(r, "max_same_category_pct", action="swap", replaced_by=swap))
                added.append(entry(swap, "max_same_category_pct", replaces=r))
                continue
            if len(counts) * pct < 1.0 - eps:
                unmet["max_same_category_pct"] = "insufficient_categories"
                break
            members = rest
            gone.add(r)
            removed.append(entry(r, "max_same_category_pct", action="trim"))

        final_set = set(members)
        final = [name for name in order if name in final_set]
        after = summary(final)
        satisfied = {
            "min_categories": after["n_categories"] >= min_c,
            "min_data_sources": after["n_data_sources"] >= min_s,
            "max_same_category_pct": (
                after["max_category_share"] is None
                or max(after["category_counts"].values()) <= pct * sum(after["category_counts"].values()) + eps
            ),
        }
        log = {
            "enabled": True,
            "settings": {k: v for k, v in settings.items() if k != "enabled"},
            "n_before": len(before),
            "n_after": len(final),
            "before": summary([name for name in order if name in set(before)]),
            "after": after,
            "satisfied": satisfied,
            "unmet_reasons": unmet,
            "added": added,
            "removed": removed,
            "metadata_missing": {
                "selected_before": missing_count(before),
                "candidates": missing_count([n for n in order if n not in selected_set]),
                "final": missing_count(final),
            },
        }
        return final, log

    def _compute_vif_scores(self, data: pd.DataFrame) -> dict[str, float]:
        vifs: dict[str, float] = {}
        matrix = data.to_numpy(dtype=float)
        for idx, feature in enumerate(data.columns):
            y = matrix[:, idx]
            x = np.delete(matrix, idx, axis=1)
            if x.size == 0:
                vifs[feature] = 1.0
                continue
            if np.nanstd(y) == 0:
                vifs[feature] = float("inf")
                continue
            try:
                model = LinearRegression()
                model.fit(x, y)
                r2 = model.score(x, y)
            except Exception as exc:  # noqa: BLE001
                logger.warning("VIF regression failed for %s: %s", feature, exc)
                vifs[feature] = float("inf")
                continue

            if r2 >= 0.999999:
                vifs[feature] = float("inf")
            else:
                vifs[feature] = float(1.0 / (1.0 - r2))
        return vifs

    @staticmethod
    def _score_value(ic_scores: dict, name: str, tiebreaker: str) -> float:
        if not ic_scores:
            return float("-inf")
        value = ic_scores.get(name)
        if isinstance(value, dict):
            score = value.get(tiebreaker)
            if score is None:
                score = value.get("icir", float("nan"))
            score_value = float(score)
            return score_value if np.isfinite(score_value) else float("-inf")
        if isinstance(value, (int, float)):
            score_value = float(value)
            return score_value if np.isfinite(score_value) else float("-inf")
        return float("-inf")

    @staticmethod
    def _compute_coverage(metadata: dict, selected: list[str], key: str) -> float:
        if not metadata:
            return 0.0

        total_values = {info.get(key) for info in metadata.values() if info}
        total_values.discard(None)
        if not total_values:
            return 0.0

        selected_values = set()
        for name in selected:
            info = metadata.get(name, {}) if metadata else {}
            value = info.get(key)
            if value is not None:
                selected_values.add(value)

        return float(len(selected_values) / len(total_values))
