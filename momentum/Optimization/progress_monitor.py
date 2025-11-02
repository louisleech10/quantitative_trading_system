"""
進度監控器 - 優化進度追蹤與實時通知

功能:
1. 實時進度追蹤（當前試驗數、完成百分比、最佳值）
2. 預計剩餘時間計算（基於平均試驗時間）
3. 階段性通知（里程碑、新最佳值）
4. WebSocket實時推送（可選）
5. 監控指標統計（試驗速度、成功率）

Author: Claude (Phase 3.5 Day 4)
Date: 2025-11-02
"""

import logging
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from optuna import Study
from optuna.trial import FrozenTrial, TrialState


@dataclass
class ProgressStats:
    """
    進度統計數據類

    Attributes:
        total_trials: 總試驗次數
        completed_trials: 已完成試驗數
        pruned_trials: 被剪枝試驗數
        failed_trials: 失敗試驗數
        best_value: 當前最佳值
        best_trial_number: 最佳試驗編號
        completion_percentage: 完成百分比
        elapsed_time: 已耗時（秒）
        estimated_remaining_time: 預計剩餘時間（秒）
        trials_per_hour: 試驗速度（trials/hour）
        avg_trial_duration: 平均單次試驗耗時（秒）
    """
    total_trials: int
    completed_trials: int = 0
    pruned_trials: int = 0
    failed_trials: int = 0
    best_value: Optional[float] = None
    best_trial_number: Optional[int] = None
    completion_percentage: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining_time: Optional[float] = None
    trials_per_hour: float = 0.0
    avg_trial_duration: float = 0.0


class ProgressMonitor:
    """
    進度監控器

    負責優化過程中的進度追蹤、統計計算和實時通知。

    核心功能:
    1. 追蹤優化進度（已完成試驗、最佳值等）
    2. 計算統計指標（完成百分比、預計剩餘時間）
    3. 階段性通知（里程碑25%/50%/75%、新最佳值）
    4. WebSocket推送支援（通過callback機制）
    5. 詳細日誌記錄

    設計理念:
    - 輕量級：最小化對優化性能的影響
    - 非侵入式：通過callback機制與OptunaOptimizer解耦
    - 可擴展：支援自定義通知管道（WebSocket、Email等）
    """

    def __init__(
        self,
        total_trials: int,
        notification_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        milestone_percentages: List[int] = None,
        log_interval: int = 100
    ):
        """
        初始化進度監控器

        Args:
            total_trials: 總試驗次數
            notification_callback: 通知回調函數，接收(event_type, data)
            milestone_percentages: 里程碑百分比列表（default: [25, 50, 75]）
            log_interval: 日誌記錄間隔（每N次試驗，default: 100）
        """
        self.total_trials = total_trials
        self.notification_callback = notification_callback
        self.milestone_percentages = milestone_percentages or [25, 50, 75]
        self.log_interval = log_interval

        # 日誌
        self.logger = logging.getLogger(__name__)

        # 進度狀態
        self.start_time: Optional[float] = None
        self.last_best_value: Optional[float] = None
        self.completed_trials: int = 0
        self.pruned_trials: int = 0
        self.failed_trials: int = 0
        self.trial_durations: List[float] = []  # 記錄最近N次試驗耗時

        # 里程碑追蹤（已達成的里程碑）
        self.reached_milestones: set = set()

        # 每次試驗開始時間（用於計算單次試驗耗時）
        self.trial_start_times: Dict[int, float] = {}

        self.logger.info(
            f"ProgressMonitor initialized: total_trials={total_trials}, "
            f"milestones={self.milestone_percentages}, log_interval={log_interval}"
        )

    def start(self):
        """開始監控（記錄開始時間）"""
        self.start_time = time.time()
        self.logger.info(f"Optimization started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 發送開始通知
        self._send_notification('optimization_started', {
            'total_trials': self.total_trials,
            'start_time': datetime.now().isoformat()
        })

    def on_trial_start(self, trial: FrozenTrial):
        """
        試驗開始回調

        Args:
            trial: Optuna Trial對象
        """
        self.trial_start_times[trial.number] = time.time()

        self.logger.debug(f"Trial {trial.number} started")

    def on_trial_complete(self, study: Study, trial: FrozenTrial):
        """
        試驗完成回調（核心方法）

        Args:
            study: Optuna Study對象
            trial: 完成的Trial對象
        """
        # 步驟1: 更新統計數據
        self._update_statistics(study, trial)

        # 步驟2: 計算進度統計
        stats = self.get_progress_stats(study)

        # 步驟3: 檢查並觸發通知
        self._check_and_notify(study, trial, stats)

        # 步驟4: 階段性日誌記錄
        if stats.completed_trials % self.log_interval == 0:
            self._log_progress(stats)

    def _update_statistics(self, study: Study, trial: FrozenTrial):
        """
        更新統計數據

        Args:
            study: Optuna Study對象
            trial: 完成的Trial對象
        """
        # 更新試驗計數
        if trial.state == TrialState.COMPLETE:
            self.completed_trials += 1
        elif trial.state == TrialState.PRUNED:
            self.pruned_trials += 1
        elif trial.state == TrialState.FAIL:
            self.failed_trials += 1

        # 更新試驗耗時記錄（保留最近100次）
        if trial.number in self.trial_start_times:
            duration = time.time() - self.trial_start_times[trial.number]
            self.trial_durations.append(duration)

            # 保留最近100次試驗耗時（用於預測剩餘時間）
            if len(self.trial_durations) > 100:
                self.trial_durations.pop(0)

            # 清理start_times記錄
            del self.trial_start_times[trial.number]

    def _check_and_notify(self, study: Study, trial: FrozenTrial, stats: ProgressStats):
        """
        檢查並觸發通知

        檢查項目:
        1. 新最佳值
        2. 里程碑（25%/50%/75%）
        3. 實時進度更新（每次試驗）

        Args:
            study: Optuna Study對象
            trial: 完成的Trial對象
            stats: 進度統計數據
        """
        # 通知1: 新最佳值
        if trial.state == TrialState.COMPLETE:
            if self.last_best_value is None or study.best_value > self.last_best_value:
                self.last_best_value = study.best_value

                self.logger.info(
                    f"🎯 New best value found: {study.best_value:.4f} "
                    f"(trial {trial.number}, params={trial.params})"
                )

                self._send_notification('new_best_value', {
                    'trial_number': trial.number,
                    'best_value': study.best_value,
                    'best_params': trial.params,
                    'completion_percentage': stats.completion_percentage
                })

        # 通知2: 里程碑
        current_percentage = int(stats.completion_percentage)
        for milestone in self.milestone_percentages:
            if current_percentage >= milestone and milestone not in self.reached_milestones:
                self.reached_milestones.add(milestone)

                self.logger.info(
                    f"🏁 Milestone reached: {milestone}% "
                    f"({stats.completed_trials}/{stats.total_trials} trials)"
                )

                self._send_notification('milestone_reached', {
                    'milestone_percentage': milestone,
                    'completed_trials': stats.completed_trials,
                    'total_trials': stats.total_trials,
                    'best_value': stats.best_value,
                    'estimated_remaining_time': stats.estimated_remaining_time
                })

        # 通知3: 實時進度更新（每次試驗）
        self._send_notification('progress_update', {
            'completed_trials': stats.completed_trials,
            'total_trials': stats.total_trials,
            'completion_percentage': stats.completion_percentage,
            'best_value': stats.best_value,
            'elapsed_time': stats.elapsed_time,
            'estimated_remaining_time': stats.estimated_remaining_time,
            'trials_per_hour': stats.trials_per_hour
        })

    def _send_notification(self, event_type: str, data: Dict[str, Any]):
        """
        發送通知（通過callback）

        Args:
            event_type: 事件類型（optimization_started/new_best_value/milestone_reached等）
            data: 事件數據
        """
        if self.notification_callback:
            try:
                self.notification_callback(event_type, data)
            except Exception as e:
                self.logger.error(
                    f"Notification callback failed for event '{event_type}': {e}",
                    exc_info=True
                )

    def _log_progress(self, stats: ProgressStats):
        """
        階段性日誌記錄

        Args:
            stats: 進度統計數據
        """
        if stats.estimated_remaining_time is not None:
            eta_str = str(timedelta(seconds=int(stats.estimated_remaining_time)))
        else:
            eta_str = "N/A"

        self.logger.info(
            f"Progress: {stats.completed_trials}/{stats.total_trials} trials "
            f"({stats.completion_percentage:.1f}%), "
            f"best={stats.best_value:.4f if stats.best_value else 'N/A'}, "
            f"speed={stats.trials_per_hour:.1f} trials/hour, "
            f"ETA={eta_str}"
        )

    def get_progress_stats(self, study: Study) -> ProgressStats:
        """
        獲取當前進度統計

        Args:
            study: Optuna Study對象

        Returns:
            ProgressStats對象
        """
        # 基礎統計
        total_finished = self.completed_trials + self.pruned_trials + self.failed_trials
        completion_percentage = (total_finished / self.total_trials * 100) if self.total_trials > 0 else 0.0

        # 時間統計
        elapsed_time = time.time() - self.start_time if self.start_time else 0.0

        # 計算平均試驗耗時（基於最近N次）
        avg_trial_duration = sum(self.trial_durations) / len(self.trial_durations) if self.trial_durations else 0.0

        # 預計剩餘時間
        remaining_trials = self.total_trials - total_finished
        estimated_remaining_time = remaining_trials * avg_trial_duration if avg_trial_duration > 0 else None

        # 試驗速度（trials/hour）
        trials_per_hour = (total_finished / elapsed_time * 3600) if elapsed_time > 0 else 0.0

        # 最佳值和試驗編號
        best_value = None
        best_trial_number = None
        if hasattr(study, 'best_trial') and study.best_trial:
            best_value = study.best_value
            best_trial_number = study.best_trial.number

        return ProgressStats(
            total_trials=self.total_trials,
            completed_trials=self.completed_trials,
            pruned_trials=self.pruned_trials,
            failed_trials=self.failed_trials,
            best_value=best_value,
            best_trial_number=best_trial_number,
            completion_percentage=completion_percentage,
            elapsed_time=elapsed_time,
            estimated_remaining_time=estimated_remaining_time,
            trials_per_hour=trials_per_hour,
            avg_trial_duration=avg_trial_duration
        )

    def finish(self, study: Study):
        """
        完成監控（優化結束時調用）

        Args:
            study: Optuna Study對象
        """
        if self.start_time is None:
            self.logger.warning("finish() called but monitoring was never started")
            return

        stats = self.get_progress_stats(study)

        self.logger.info(
            f"Optimization finished: {stats.completed_trials} completed, "
            f"{stats.pruned_trials} pruned, {stats.failed_trials} failed, "
            f"total time={timedelta(seconds=int(stats.elapsed_time))}, "
            f"best_value={stats.best_value:.4f if stats.best_value else 'N/A'}"
        )

        # 發送完成通知
        self._send_notification('optimization_finished', {
            'total_trials': stats.total_trials,
            'completed_trials': stats.completed_trials,
            'pruned_trials': stats.pruned_trials,
            'failed_trials': stats.failed_trials,
            'best_value': stats.best_value,
            'best_trial_number': stats.best_trial_number,
            'elapsed_time': stats.elapsed_time,
            'avg_trial_duration': stats.avg_trial_duration
        })

    def get_summary(self, study: Study) -> Dict[str, Any]:
        """
        獲取優化摘要

        Args:
            study: Optuna Study對象

        Returns:
            摘要字典
        """
        stats = self.get_progress_stats(study)

        return {
            'total_trials': stats.total_trials,
            'completed_trials': stats.completed_trials,
            'pruned_trials': stats.pruned_trials,
            'failed_trials': stats.failed_trials,
            'success_rate': stats.completed_trials / max(stats.total_trials, 1),
            'best_value': stats.best_value,
            'best_trial_number': stats.best_trial_number,
            'elapsed_time': stats.elapsed_time,
            'avg_trial_duration': stats.avg_trial_duration,
            'trials_per_hour': stats.trials_per_hour,
            'milestones_reached': sorted(list(self.reached_milestones))
        }
