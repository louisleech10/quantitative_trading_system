"""
檢查點管理器 - 斷點續跑機制

功能:
1. 手動檢查點保存（每50次試驗）
2. 檢查點載入與恢復
3. 檢查點驗證與完整性檢查
4. 與Optuna SQLite持久化協同工作

設計理念:
- Optuna原生SQLite已提供基礎斷點續跑
- CheckpointManager提供額外保護層（數據備份、統計分析）
- 檢查點包含：最佳參數、試驗歷史、統計信息、收斂曲線

Author: Claude (Phase 3.5 Day 3)
Date: 2025-11-02
"""

import logging
import pickle
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from optuna import Study

class CheckpointManager:
    """
    檢查點管理器

    負責優化過程中的檢查點保存、載入和驗證。
    與Optuna SQLite持久化協同工作，提供額外數據保護。
    """

    def __init__(
        self,
        checkpoint_dir: str = "data/checkpoints",
        save_interval: int = 50,
        max_checkpoints: int = 10
    ):
        """
        初始化檢查點管理器

        Args:
            checkpoint_dir: 檢查點保存目錄
            save_interval: 保存間隔（每N次試驗保存一次）
            max_checkpoints: 最大保存檢查點數量（超過則刪除舊檢查點）
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.save_interval = save_interval
        self.max_checkpoints = max_checkpoints
        self.logger = logging.getLogger(__name__)

        # 確保檢查點目錄存在
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"CheckpointManager initialized: dir={checkpoint_dir}, "
            f"interval={save_interval}, max={max_checkpoints}"
        )

    def should_save_checkpoint(self, trial_number: int) -> bool:
        """
        判斷是否應該保存檢查點

        Args:
            trial_number: 當前試驗編號

        Returns:
            True if應該保存，False otherwise
        """
        # 每save_interval次試驗保存一次
        return trial_number > 0 and trial_number % self.save_interval == 0

    def save_checkpoint(
        self,
        study: Study,
        trial_number: int,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        保存檢查點

        Args:
            study: Optuna Study對象
            trial_number: 當前試驗編號
            additional_data: 額外數據（可選）

        Returns:
            檢查點文件路徑

        Raises:
            IOError: 保存失敗時拋出
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_name = f"checkpoint_trial_{trial_number}_{timestamp}.pkl"
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        try:
            # 收集檢查點數據
            checkpoint_data = {
                'trial_number': trial_number,
                'timestamp': timestamp,
                'study_name': study.study_name,
                'best_params': study.best_params if hasattr(study, 'best_params') else None,
                'best_value': study.best_value if hasattr(study, 'best_value') else None,
                'best_trial_number': study.best_trial.number if hasattr(study, 'best_trial') else None,
                'n_trials': len(study.trials),
                'trials_dataframe': study.trials_dataframe(),
                'user_attrs': study.user_attrs,
                'system_attrs': study.system_attrs,
            }

            # 添加統計信息
            if len(study.trials) > 0:
                df = study.trials_dataframe()
                completed_trials = df[df['state'] == 'COMPLETE']

                if len(completed_trials) > 0:
                    checkpoint_data['statistics'] = {
                        'n_completed': len(completed_trials),
                        'n_pruned': len(df[df['state'] == 'PRUNED']),
                        'n_failed': len(df[df['state'] == 'FAIL']),
                        'mean_value': completed_trials['value'].mean() if 'value' in completed_trials.columns else None,
                        'std_value': completed_trials['value'].std() if 'value' in completed_trials.columns else None,
                        'min_value': completed_trials['value'].min() if 'value' in completed_trials.columns else None,
                        'max_value': completed_trials['value'].max() if 'value' in completed_trials.columns else None,
                    }

            # 添加額外數據
            if additional_data:
                checkpoint_data['additional_data'] = additional_data

            # 保存到pickle文件
            with open(checkpoint_path, 'wb') as f:
                pickle.dump(checkpoint_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.logger.info(
                f"Checkpoint saved: trial={trial_number}, "
                f"best_value={checkpoint_data.get('best_value')}, "
                f"path={checkpoint_path}"
            )

            # 清理舊檢查點
            self._cleanup_old_checkpoints()

            return str(checkpoint_path)

        except Exception as e:
            self.logger.error(
                f"Failed to save checkpoint at trial {trial_number}: {e}",
                exc_info=True
            )
            raise IOError(f"Checkpoint save failed: {e}")

    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """
        載入檢查點

        Args:
            checkpoint_path: 檢查點文件路徑

        Returns:
            檢查點數據字典

        Raises:
            FileNotFoundError: 檢查點不存在
            IOError: 載入失敗
        """
        checkpoint_path = Path(checkpoint_path)

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)

            self.logger.info(
                f"Checkpoint loaded: trial={checkpoint_data.get('trial_number')}, "
                f"best_value={checkpoint_data.get('best_value')}"
            )

            return checkpoint_data

        except Exception as e:
            self.logger.error(
                f"Failed to load checkpoint from {checkpoint_path}: {e}",
                exc_info=True
            )
            raise IOError(f"Checkpoint load failed: {e}")

    def list_checkpoints(self, study_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有檢查點

        Args:
            study_name: 過濾特定Study的檢查點（可選）

        Returns:
            檢查點信息列表，每個元素包含：
            {
                'path': str,
                'trial_number': int,
                'timestamp': str,
                'study_name': str,
                'best_value': float,
                'file_size': int (bytes)
            }
        """
        checkpoints = []

        for checkpoint_file in sorted(self.checkpoint_dir.glob("checkpoint_*.pkl")):
            try:
                # 讀取檢查點基本信息（不完整載入，僅讀取元數據）
                with open(checkpoint_file, 'rb') as f:
                    data = pickle.load(f)

                # 過濾study_name
                if study_name and data.get('study_name') != study_name:
                    continue

                checkpoint_info = {
                    'path': str(checkpoint_file),
                    'trial_number': data.get('trial_number'),
                    'timestamp': data.get('timestamp'),
                    'study_name': data.get('study_name'),
                    'best_value': data.get('best_value'),
                    'file_size': checkpoint_file.stat().st_size
                }

                checkpoints.append(checkpoint_info)

            except Exception as e:
                self.logger.warning(
                    f"Failed to read checkpoint {checkpoint_file}: {e}"
                )
                continue

        # 按trial_number降序排序（最新的在前）
        checkpoints.sort(key=lambda x: x['trial_number'], reverse=True)

        return checkpoints

    def validate_checkpoint(self, checkpoint_path: str) -> bool:
        """
        驗證檢查點完整性

        Args:
            checkpoint_path: 檢查點文件路徑

        Returns:
            True if驗證通過，False otherwise
        """
        try:
            checkpoint_data = self.load_checkpoint(checkpoint_path)

            # 驗證必要欄位
            required_fields = ['trial_number', 'timestamp', 'study_name']
            for field in required_fields:
                if field not in checkpoint_data:
                    self.logger.error(f"Checkpoint missing required field: {field}")
                    return False

            # 驗證trials_dataframe
            if 'trials_dataframe' in checkpoint_data:
                df = checkpoint_data['trials_dataframe']
                if not isinstance(df, pd.DataFrame):
                    self.logger.error("trials_dataframe is not a DataFrame")
                    return False

            self.logger.info(f"Checkpoint validation passed: {checkpoint_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Checkpoint validation failed: {e}",
                exc_info=True
            )
            return False

    def get_latest_checkpoint(self, study_name: Optional[str] = None) -> Optional[str]:
        """
        獲取最新檢查點路徑

        Args:
            study_name: 過濾特定Study（可選）

        Returns:
            最新檢查點路徑，若無則返回None
        """
        checkpoints = self.list_checkpoints(study_name)

        if checkpoints:
            return checkpoints[0]['path']  # 已按trial_number降序排序

        return None

    def _cleanup_old_checkpoints(self):
        """
        清理舊檢查點（保留最新的max_checkpoints個）
        """
        checkpoints = self.list_checkpoints()

        if len(checkpoints) > self.max_checkpoints:
            # 刪除超出限制的舊檢查點
            to_delete = checkpoints[self.max_checkpoints:]

            for checkpoint in to_delete:
                try:
                    os.remove(checkpoint['path'])
                    self.logger.info(
                        f"Deleted old checkpoint: trial={checkpoint['trial_number']}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to delete checkpoint {checkpoint['path']}: {e}"
                    )

    def export_checkpoint_summary(
        self,
        checkpoint_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        導出檢查點摘要（CSV格式）

        Args:
            checkpoint_path: 檢查點文件路徑
            output_path: 輸出CSV路徑（可選，默認與checkpoint同名）

        Returns:
            輸出CSV路徑
        """
        checkpoint_data = self.load_checkpoint(checkpoint_path)

        if output_path is None:
            output_path = str(Path(checkpoint_path).with_suffix('.csv'))

        # 導出trials_dataframe
        df = checkpoint_data.get('trials_dataframe')
        if df is not None:
            df.to_csv(output_path, index=False)
            self.logger.info(f"Checkpoint summary exported to {output_path}")
        else:
            self.logger.warning("No trials_dataframe found in checkpoint")

        return output_path
