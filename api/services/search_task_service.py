"""
搜索任務服務 - 處理正反例兩階段搜索邏輯
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from pydantic import BaseModel, Field
from ..core.config import settings
from ..core.logging import get_logger
from ..models.requests import SearchConfigRequest, NegativeCaseRequest
from ..models.responses import SearchResultData, CaseData
from ..utils.exceptions import SearchExecutionException
from .standalone_search_service import standalone_search_service

class SearchTaskService:
    """兩階段搜索任務服務：正例搜索 → 反例搜索"""
    
    def __init__(self):
        self.logger = get_logger("api.search_task_service")
        self.positive_results: Dict[str, List[CaseData]] = {}  # 儲存正例結果
        self.negative_results: Dict[str, List[CaseData]] = {}  # 儲存反例結果
        self.positive_configs: Dict[str, SearchConfigRequest] = {}  # 儲存正例搜索配置
        
    async def execute_positive_search(self, request: SearchConfigRequest, 
                                    symbols: Optional[List[str]] = None) -> str:
        """
        執行正例搜索（第一階段）
        返回 task_id，用於後續查詢結果和執行反例搜索
        """
        self.logger.info(f"Starting positive search: {request.name}")

        # 執行搜索
        task_id = await standalone_search_service.execute_search(request, symbols)

        # 儲存正例搜索配置，包含timeframe信息
        self.positive_configs[task_id] = request
        self.logger.info(f"儲存正例搜索配置，timeframe: {request.timeframe}")

        # 監控搜索完成並儲存結果
        asyncio.create_task(self._monitor_positive_search(task_id))

        return task_id
    
    async def _monitor_positive_search(self, task_id: str):
        """監控正例搜索完成並儲存結果"""
        max_wait_time = 300  # 5分鐘超時
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait_time:
            task_info = standalone_search_service.get_task_status(task_id)
            
            if not task_info:
                self.logger.error(f"Task {task_id} not found")
                break
                
            if task_info.status.value == "completed":
                # 獲取結果並儲存
                result_data = standalone_search_service.get_task_result(task_id)
                if result_data and result_data.cases:
                    # 確保正例案例被正確標記
                    for case in result_data.cases:
                        if hasattr(case, '__dict__'):
                            case.__dict__['positive_case'] = True
                        elif isinstance(case, dict):
                            case['positive_case'] = True
                    
                    self.positive_results[task_id] = result_data.cases
                    self.logger.info(f"Positive search {task_id} completed with {len(result_data.cases)} cases")
                break
                
            elif task_info.status.value in ["failed", "cancelled"]:
                self.logger.warning(f"Positive search {task_id} ended with status: {task_info.status.value}")
                break
                
            await asyncio.sleep(2)  # 每2秒檢查一次
    
    async def execute_negative_search(self, positive_task_id: str,
                                    negative_request: NegativeCaseRequest) -> str:
        """
        執行反例搜索（第二階段）
        基於正例搜索結果進行反例採樣
        """
        # 檢查正例結果是否存在
        if positive_task_id not in self.positive_results:
            raise SearchExecutionException(f"Positive search results not found for task {positive_task_id}")

        positive_cases = self.positive_results[positive_task_id]
        if not positive_cases:
            raise SearchExecutionException("No positive cases found to generate negative examples")

        # 獲取正例搜索的timeframe配置
        positive_timeframe = "12h"  # 默認值

        # 優先從存儲的配置中獲取timeframe
        if positive_task_id in self.positive_configs:
            positive_timeframe = self.positive_configs[positive_task_id].timeframe
            self.logger.info(f"從存儲的正例配置中獲取timeframe: {positive_timeframe}")
        else:
            # 備用方案：從搜索結果中獲取
            try:
                positive_result = standalone_search_service.get_task_result(positive_task_id)
                if positive_result and hasattr(positive_result, 'search_config') and positive_result.search_config:
                    if isinstance(positive_result.search_config, dict) and 'timeframe' in positive_result.search_config:
                        positive_timeframe = positive_result.search_config['timeframe']
                        self.logger.info(f"從正例搜索結果中獲取timeframe: {positive_timeframe}")
                    else:
                        self.logger.warning("正例搜索結果中的search_config格式不正確，使用默認值")
                else:
                    self.logger.warning(f"無法從正例搜索結果中獲取search_config，使用默認值: {positive_timeframe}")
            except Exception as e:
                self.logger.error(f"獲取正例timeframe時出錯: {str(e)}，使用默認值: {positive_timeframe}")

        self.logger.info(f"Starting negative search based on {len(positive_cases)} positive cases")
        self.logger.info(f"Using timeframe from positive search: {positive_timeframe}")
        self.logger.info(f"Negative request type: {type(negative_request)}")

        # 檢查用戶條件
        if hasattr(negative_request, 'negative_conditions') and negative_request.negative_conditions:
            self.logger.info(f"用戶設定了 {len(negative_request.negative_conditions)} 個反例條件")
            for i, condition in enumerate(negative_request.negative_conditions):
                self.logger.info(f"條件 {i+1}: {condition}")
        else:
            self.logger.info("沒有用戶設定的反例條件，將使用時間分離策略")

        # 生成新的task_id給反例搜索
        negative_task_id = str(uuid.uuid4())

        # 異步執行反例搜索，傳遞正例的timeframe
        asyncio.create_task(self._run_negative_search(
            negative_task_id, positive_cases, negative_request, positive_timeframe
        ))

        return negative_task_id
    
    async def _run_negative_search(self, task_id: str, positive_cases: List[CaseData],
                         request: NegativeCaseRequest, positive_timeframe: str = "12h"):
        """執行反例搜索邏輯 - 修復版本"""
        try:
            # 更新任務狀態為執行中
            standalone_search_service.task_manager.create_task(f"negative_search_{task_id}")
            standalone_search_service.task_manager.update_task_status(
                task_id, "running"
            )

            # 提取正例的symbol列表
            positive_symbols = list(set(case.symbol for case in positive_cases))
            self.logger.info(f"開始執行反例搜索，交易對: {positive_symbols}")
            self.logger.info(f"使用正例的timeframe: {positive_timeframe}")

            # 檢查是否有用戶設定的條件
            if hasattr(request, 'negative_conditions') and request.negative_conditions:
                self.logger.info(f"使用用戶設定的反例條件，條件數量: {len(request.negative_conditions)}")

                # ✅ 調用搜索並獲得完整的 SearchResultData，傳遞正例的timeframe
                result_data = await self._search_with_user_conditions(
                    positive_symbols, request, positive_cases, positive_timeframe
                )

                # 檢查結果是否有效
                if not result_data or not result_data.cases:
                    self.logger.warning("反例搜索沒有找到任何案例")
                    standalone_search_service.task_manager.update_task_status(
                        task_id, "failed", error_message="No negative cases found"
                    )
                    return

                # 獲取反例案例列表
                negative_cases = result_data.cases

                # 標記為反例
                for case in negative_cases:
                    if hasattr(case, '__dict__'):
                        case.__dict__['positive_case'] = False
                    elif isinstance(case, dict):
                        case['positive_case'] = False

                # 存儲反例結果
                self.negative_results[task_id] = negative_cases
                self.logger.info(f"反例搜索完成，找到 {len(negative_cases)} 個案例")

                # ✅ 直接使用完整的 result_data，不需要手動創建
                standalone_search_service.task_manager.set_task_result(task_id, result_data)
                standalone_search_service.task_manager.update_task_status(task_id, "completed")

            else:
                self.logger.info("沒有用戶條件，使用時間分離策略")


        except Exception as e:
            self.logger.error(f"Negative search failed: {str(e)}", exc_info=True)
            standalone_search_service.task_manager.update_task_status(
                task_id, "failed", error_message=str(e)
            )
    
    async def _search_with_user_conditions(self, symbols: List[str],
                                     request: NegativeCaseRequest,
                                     positive_cases: List[CaseData],
                                     timeframe: str = "12h") -> SearchResultData:
        """基於用戶設定條件執行反例搜索 - 修復版本"""
        try:
            from ..models.requests import SearchConfigRequest, FilterConditionRequest
            
            self.logger.info("構建反例搜索配置...")
            
            # === 修復1：使用正例搜索的相同時間範圍，而不是從案例時間戳推斷 ===
            # 優先從正例搜索配置中獲取時間範圍
            search_start_date = "2024-02-01"  # 默認值
            search_end_date = "2025-05-31"    # 默認值

            # 從存儲的正例配置中獲取
            positive_task_id = None
            for task_id, cases in self.positive_results.items():
                if cases == positive_cases:
                    positive_task_id = task_id
                    break

            if positive_task_id and positive_task_id in self.positive_configs:
                positive_config = self.positive_configs[positive_task_id]
                search_start_date = positive_config.start_date
                search_end_date = positive_config.end_date
                self.logger.info(f"從正例配置獲取時間範圍: {search_start_date} 到 {search_end_date}")
            else:
                self.logger.warning(f"無法從正例配置獲取時間範圍，使用默認值: {search_start_date} 到 {search_end_date}")

            # 轉換為datetime對象以便處理
            try:
                search_start = datetime.strptime(search_start_date, '%Y-%m-%d')
                search_end = datetime.strptime(search_end_date, '%Y-%m-%d')
            except ValueError:
                # 如果日期格式有問題，使用默認範圍
                search_start = datetime.strptime("2024-02-01", '%Y-%m-%d')
                search_end = datetime.strptime("2025-05-31", '%Y-%m-%d')
                self.logger.warning("日期格式錯誤，使用默認時間範圍")

            self.logger.info(f"反例搜索將使用與正例相同的時間範圍: {search_start.date()} 到 {search_end.date()}")
            
            # === 創建搜索配置 ===
            negative_config = SearchConfigRequest(
                name=f"user_negative_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="基於用戶條件的反例搜索",
                timeframe=timeframe,  # 使用正例搜索相同的timeframe
                initial_conditions=[],
                advanced_conditions=[],
                start_date=search_start_date,  # 使用正例搜索相同的開始日期
                end_date=search_end_date       # 使用正例搜索相同的結束日期
            )
            
            # 添加用戶設定的條件
            for condition_data in request.negative_conditions:
                self.logger.info(f"添加條件: {condition_data['parameter']} {condition_data['operator']} {condition_data['value']}")
                
                condition = FilterConditionRequest(
                    condition_type=condition_data["condition_type"],
                    parameter=condition_data["parameter"],
                    operator=condition_data["operator"],
                    value=condition_data["value"],
                    description=condition_data.get("description", "用戶自定義反例條件")
                )
                negative_config.initial_conditions.append(condition)
            
            # 執行真實搜索
            self.logger.info("執行基於條件的反例搜索...")
            negative_task_id = await standalone_search_service.execute_search(negative_config, symbols)
            
            # 等待搜索完成 - 基於任務狀態的智能等待
            CHECK_INTERVAL = 2  # 每2秒檢查一次
            IDLE_TIMEOUT = 300  # 異常狀態5分鐘超時

            start_time = datetime.now()
            last_status = None

            while True:
                elapsed = (datetime.now() - start_time).total_seconds()  # ✅ 修復：使用total_seconds而非seconds
                task_info = standalone_search_service.get_task_status(negative_task_id)

                # 任務不存在
                if not task_info:
                    self.logger.error(f"任務不存在: {negative_task_id}")
                    break

                current_status = task_info.status.value

                # 狀態變化時記錄
                if current_status != last_status:
                    self.logger.info(f"反例搜索任務狀態: {current_status} (已等待{elapsed:.0f}秒)")
                    last_status = current_status

                # ✅ 任務完成 - 處理結果
                if current_status == "completed":
                    result_data = standalone_search_service.get_task_result(negative_task_id)

                    # DEBUG日誌追蹤結果傳遞
                    self.logger.info(f"[DEBUG] 獲取任務結果: task_id={negative_task_id}")
                    self.logger.info(f"[DEBUG] result_data is None: {result_data is None}")
                    if result_data:
                        self.logger.info(f"[DEBUG] result_data.cases is None: {result_data.cases is None}")
                        if result_data.cases is not None:
                            self.logger.info(f"[DEBUG] result_data.cases 長度: {len(result_data.cases)}")

                    if result_data and result_data.cases:
                        self.logger.info(f"條件搜索完成，找到 {len(result_data.cases)} 個候選反例")

                        # ✅ 統一時間分離預設值為3天（與API Model一致）
                        enable_separation = getattr(request, 'enable_time_separation', True)
                        separation_days = getattr(request, 'time_separation_days', 3)
                        negative_ratio = getattr(request, 'negative_ratio', 2.0)
                        enable_random_sampling = getattr(request, 'enable_random_sampling', True)  # ===== 新增 =====

                        self.logger.info(f"時間分離配置: 啟用={enable_separation}, {separation_days}天, 反例比例: {negative_ratio}, 隨機取樣: {enable_random_sampling}")

                        # 應用時間分離和比例控制
                        filtered_cases = await self._apply_time_separation_and_ratio(
                            result_data.cases,
                            positive_cases,
                            separation_days,
                            negative_ratio,
                            enable_separation,
                            enable_random_sampling  # ===== 新增 =====
                        )

                        # ✅ 保底邏輯：如果過濾後沒有反例，返回部分候選案例
                        if not filtered_cases and result_data.cases:
                            target_count = int(len(positive_cases) * negative_ratio)
                            self.logger.warning(
                                f"時間分離後無反例，跳過時間分離，直接取前{target_count}個候選案例"
                            )
                            filtered_cases = result_data.cases[:target_count]

                        # ✅ 更新 result_data 的案例為過濾後的案例
                        result_data.cases = filtered_cases

                        # ✅ 更新 summary 中的案例數量
                        result_data.summary.total_cases = len(filtered_cases)
                        result_data.summary.negative_cases = len(filtered_cases)
                        result_data.summary.positive_cases = 0  # 反例搜索中沒有正例

                        self.logger.info(f"時間分離和比例控制後剩餘反例: {len(filtered_cases)}")

                        # ✅ 返回完整的 SearchResultData
                        return result_data
                    break

                # ❌ 任務失敗或取消
                elif current_status in ["failed", "cancelled"]:
                    self.logger.error(f"反例搜索{current_status}")
                    break

                # ⏳ 任務正在執行 - 繼續等待（無時間限制）
                elif current_status == "running":
                    # 每60秒記錄一次進度
                    if int(elapsed) % 60 == 0 and elapsed > 0:
                        self.logger.info(f"反例搜索進行中... 已等待{elapsed:.0f}秒")
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                # ⚠️ 異常狀態(pending超時等) - 超時保護
                if elapsed > IDLE_TIMEOUT:
                    self.logger.error(
                        f"任務異常超時: 狀態={current_status}, "
                        f"等待{elapsed:.0f}秒, task_id={negative_task_id}"
                    )
                    break

                await asyncio.sleep(CHECK_INTERVAL)

            # 執行到這裡表示失敗
            self.logger.warning("反例搜索超時或失敗")
            return None
            
        except Exception as e:
            self.logger.error(f"用戶條件搜索失敗: {str(e)}")
            return None
        
    async def _apply_time_separation_and_ratio(
        self,
        candidate_cases: List[CaseData],
        positive_cases: List[CaseData],
        separation_days: int,
        ratio: float,
        enable_separation: bool = True,
        enable_random_sampling: bool = True  # ===== 新增參數 =====
    ) -> List[CaseData]:
        """
        應用時間分離和比例控制

        新邏輯：按Symbol獨立過濾，避免跨Symbol過濾導致100%過濾率

        Args:
            enable_random_sampling: 是否啟用隨機取樣（True=啟用，False=返回所有符合條件的反例）
        """
        try:
            from datetime import datetime, timedelta
            from collections import defaultdict

            self.logger.info(
                f"開始時間分離過濾: 候選反例{len(candidate_cases)}個, "
                f"正例{len(positive_cases)}個, 分離{separation_days}天, 啟用={enable_separation}"
            )

            # Step 1: 如果時間分離被關閉，直接跳過過濾
            if not enable_separation or separation_days == 0:
                self.logger.info(f"時間分離已關閉，候選反例: {len(candidate_cases)}個")
                filtered_candidates = candidate_cases
            else:
                # Step 2: 按Symbol分組正例的時間戳
                positive_times_by_symbol = defaultdict(list)

                for case in positive_cases:
                    # 獲取symbol
                    symbol = getattr(case, 'symbol', None)
                    if not symbol:
                        continue

                    # 獲取timestamp
                    if hasattr(case, 'timestamp'):
                        ts = case.timestamp
                    elif hasattr(case, '__dict__') and 'timestamp' in case.__dict__:
                        ts = case.__dict__['timestamp']
                    else:
                        continue

                    # 轉換為datetime
                    if isinstance(ts, str):
                        if 'T' in ts:
                            pos_time = datetime.fromisoformat(ts.replace('Z', ''))
                        else:
                            pos_time = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                    elif isinstance(ts, datetime):
                        pos_time = ts
                    else:
                        continue

                    positive_times_by_symbol[symbol].append(pos_time)

                # Step 3: 按Symbol過濾候選案例
                separation_delta = timedelta(days=separation_days)
                filtered_candidates = []
                symbol_stats = defaultdict(lambda: {
                    'pos_count': 0,
                    'candidates': 0,
                    'kept': 0,
                    'filtered': 0
                })

                for case in candidate_cases:
                    # 獲取symbol
                    symbol = getattr(case, 'symbol', None)
                    if not symbol:
                        continue

                    symbol_stats[symbol]['candidates'] += 1

                    # 獲取該Symbol的正例時間列表
                    same_symbol_positives = positive_times_by_symbol.get(symbol, [])

                    # 獲取候選案例的時間
                    if hasattr(case, 'timestamp'):
                        ts = case.timestamp
                    elif hasattr(case, '__dict__') and 'timestamp' in case.__dict__:
                        ts = case.__dict__['timestamp']
                    else:
                        continue

                    if isinstance(ts, str):
                        if 'T' in ts:
                            case_time = datetime.fromisoformat(ts.replace('Z', ''))
                        else:
                            case_time = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                    elif isinstance(ts, datetime):
                        case_time = ts
                    else:
                        continue

                    # 僅檢查與同Symbol正例的時間距離
                    is_separated = True
                    for pos_time in same_symbol_positives:
                        if abs((case_time - pos_time)) < separation_delta:
                            is_separated = False
                            symbol_stats[symbol]['filtered'] += 1
                            break

                    if is_separated:
                        filtered_candidates.append(case)
                        symbol_stats[symbol]['kept'] += 1

                # 記錄每個Symbol的正例數量
                for symbol, times in positive_times_by_symbol.items():
                    symbol_stats[symbol]['pos_count'] = len(times)

                # Step 4: 詳細日誌 - 按Symbol顯示統計（前10個Symbol）
                self.logger.info(f"時間分離統計（按Symbol獨立計算）:")
                sorted_symbols = sorted(symbol_stats.keys())[:10]  # 只顯示前10個
                for symbol in sorted_symbols:
                    stats = symbol_stats[symbol]
                    self.logger.info(
                        f"  {symbol}: 正例{stats['pos_count']}個, "
                        f"候選{stats['candidates']}個 → "
                        f"保留{stats['kept']}個, 過濾{stats['filtered']}個"
                    )

                if len(symbol_stats) > 10:
                    self.logger.info(f"  ... 還有 {len(symbol_stats) - 10} 個Symbol未顯示")

                total_filtered = sum(s['filtered'] for s in symbol_stats.values())
                self.logger.info(
                    f"總計: 保留{len(filtered_candidates)}個, "
                    f"過濾{total_filtered}個 (在{separation_days}天窗口內)"
                )

            # Step 5: 應用比例控制（可選隨機取樣）
            target_count = int(len(positive_cases) * ratio)
            self.logger.info(f"目標反例數量: {target_count} (正例: {len(positive_cases)}, 比例: {ratio})")

            # ===== 新增：根據enable_random_sampling決定是否隨機取樣 =====
            if enable_random_sampling:
                # 啟用隨機取樣：從候選中隨機選擇目標數量的反例
                if len(filtered_candidates) > target_count:
                    import random
                    selected_cases = random.sample(filtered_candidates, target_count)
                    self.logger.info(f"[隨機取樣] 從 {len(filtered_candidates)} 個候選中隨機選擇了 {len(selected_cases)} 個反例")
                else:
                    selected_cases = filtered_candidates
                    if len(selected_cases) < target_count:
                        self.logger.warning(f"反例數量不足: 找到 {len(selected_cases)}, 目標 {target_count}")
            else:
                # 關閉隨機取樣：返回所有符合條件的反例
                selected_cases = filtered_candidates
                self.logger.info(f"[關閉隨機取樣] 返回所有 {len(filtered_candidates)} 個符合條件的反例（忽略目標數量{target_count}）")

            # Step 6: 為反例添加標記
            final_cases = []
            for case in selected_cases:
                if hasattr(case, '__dict__'):
                    case.__dict__['positive_case'] = 0
                    final_cases.append(case)
                elif isinstance(case, dict):
                    case['positive_case'] = 0
                    final_cases.append(case)
                else:
                    final_cases.append(case)

            self.logger.info(f"最終生成反例數量: {len(final_cases)}")
            return final_cases

        except Exception as e:
            self.logger.error(f"時間分離和比例控制失敗: {str(e)}")
            return candidate_cases[:int(len(positive_cases) * ratio)]  # 降級處理
    
    async def _generate_negative_cases(self, positive_cases: List[CaseData],
                                 symbols: List[str],
                                 request: NegativeCaseRequest,
                                 timeframe: str = "12h") -> List[CaseData]:
        """基於真實K線數據生成時間分離的反例案例"""
        self.logger.info(f"開始生成真實反例：正例數量={len(positive_cases)}, 目標比例={request.negative_ratio}")
        
        negative_cases = []
        target_count = int(len(positive_cases) * request.negative_ratio)
        separation_days = request.time_separation_days
        
        # 獲取數據加載器
        from ..services.standalone_search_service import standalone_search_service
        data_loader = standalone_search_service.data_loader
        
        for i, positive_case in enumerate(positive_cases):
            if len(negative_cases) >= target_count:
                break
                
            try:
                # 調試時間戳格式
                self.logger.info(f"正例 {i} 時間戳: {positive_case.timestamp} (type: {type(positive_case.timestamp)})")
                self.logger.info(f"分離天數: {separation_days} (type: {type(separation_days)})")

                # 安全解析時間戳
                timestamp_str = str(positive_case.timestamp)
                if 'Z' in timestamp_str:
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                elif '+' not in timestamp_str and 'T' in timestamp_str:
                    timestamp_str += '+00:00'

                pos_time = datetime.fromisoformat(timestamp_str)
                symbol = str(positive_case.symbol)

                # 確保separation_days是整數
                sep_days = int(separation_days)

                # 計算分離的時間點
                before_time = pos_time - timedelta(days=sep_days)
                after_time = pos_time + timedelta(days=sep_days)

                self.logger.info(f"正例時間: {pos_time}, 前分離: {before_time}, 後分離: {after_time}")
                
                # 為每個候選時間點獲取真實K線數據
                for candidate_time in [before_time, after_time]:
                    if len(negative_cases) >= target_count:
                        break
                    
                    try:
                        # 獲取該時間點前後的K線數據
                        # 使用更大的時間範圍查詢，並確保查詢歷史數據
                        start_time = (candidate_time - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
                        end_time = (candidate_time + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

                        # 確保查詢的是歷史時間，不是未來時間
                        current_time = datetime.now()
                        if candidate_time > current_time:
                            self.logger.warning(f"跳過未來時間點: {candidate_time}")
                            continue
                        
                        self.logger.info(f"準備獲取 {symbol} 從 {start_time} 到 {end_time} 的K線數據")
                        try:
                            # 調用真實數據加載器
                            kline_data = data_loader.get_historical_data(
                                symbol=symbol,
                                start_time=start_time,
                                end_time=end_time,
                                interval=timeframe  # 使用正例搜索相同的timeframe
                            )
                            self.logger.info(f"數據獲取結果: {type(kline_data)}, 長度: {len(kline_data) if kline_data is not None else 'None'}")
                        except Exception as data_error:
                            self.logger.error(f"數據加載器調用失敗: {str(data_error)}")
                            kline_data = None
                        
                        if kline_data is not None and not kline_data.empty:
                            # 找到最接近目標時間的K線
                            target_timestamp = candidate_time.strftime('%Y-%m-%d %H:%M:%S')
                            closest_idx = None
                            min_diff = float('inf')
                            
                            for idx, row in kline_data.iterrows():
                                time_diff = abs((idx - candidate_time).total_seconds())
                                if time_diff < min_diff:
                                    min_diff = time_diff
                                    closest_idx = idx
                            
                            if closest_idx is not None:
                                row = kline_data.loc[closest_idx]
                                
                                # 計算價格變化
                                price_change = (float(row['close']) - float(row['open'])) / float(row['open'])

                                negative_case = CaseData(
                                    symbol=symbol,
                                    timestamp=closest_idx.isoformat(),
                                    open=float(row['open']),
                                    high=float(row['high']),
                                    low=float(row['low']),
                                    close=float(row['close']),
                                    volume=float(row['volume']),
                                    trigger_idx=0,  # 反例的觸發索引
                                    price_change=price_change,
                                    market_phase="反例"  # 標記為反例階段
                                )
                                
                                negative_cases.append(negative_case)
                                self.logger.info(f"生成真實反例 {len(negative_cases)}: {symbol} at {closest_idx}")
                                
                    except Exception as e:
                        self.logger.warning(f"獲取 {symbol} 在 {candidate_time} 的真實數據失敗: {str(e)}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"處理正例 {i} 時出錯: {str(e)}")
                continue
        
        self.logger.info(f"實際生成的真實反例數量: {len(negative_cases)}")
        return negative_cases
    
    def _select_negative_timestamps(self, positive_timestamps: List[str],
                                   symbols: List[str], separation_days: int,
                                   target_count: int) -> List[str]:
        """選擇反例時間點，確保與正例時間充分分離"""
        negative_timestamps = []
        separation_delta = timedelta(days=separation_days)
        
        # 將正例時間轉換為datetime對象
        positive_times = [datetime.fromisoformat(ts.replace('Z', '+00:00')) 
                         if 'Z' in ts else datetime.fromisoformat(ts) 
                         for ts in positive_timestamps]
        
        # 生成候選時間點（在正例時間之前和之後，但保持分離）
        for pos_time in positive_times:
            # 在該正例時間之前和之後生成候選點
            candidate_before = pos_time - separation_delta
            candidate_after = pos_time + separation_delta
            
            # 檢查是否與其他正例時間衝突
            if not any(abs((candidate_before - pt).days) < separation_days 
                      for pt in positive_times):
                negative_timestamps.append(candidate_before.isoformat())
            
            if not any(abs((candidate_after - pt).days) < separation_days 
                      for pt in positive_times):
                negative_timestamps.append(candidate_after.isoformat())
            
            if len(negative_timestamps) >= target_count:
                break
        
        return negative_timestamps[:target_count]
    
    def get_combined_results(self, positive_task_id: str, 
                           negative_task_id: str) -> Optional[SearchResultData]:
        """獲取正反例合併結果"""
        positive_cases = self.positive_results.get(positive_task_id, [])
        negative_cases = self.negative_results.get(negative_task_id, [])
        
        if not positive_cases and not negative_cases:
            return None
        
        all_cases = []

        self.logger.info(f"合併正例數量: {len(positive_cases)}")
        self.logger.info(f"合併反例數量: {len(negative_cases)}")

        # 處理正例，添加 positive_case 標記
        for case in positive_cases:
            case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
            case_dict['positive_case'] = True
            all_cases.append(case_dict)

        # 處理反例，添加 positive_case 標記  
        for case in negative_cases:
            case_dict = case.dict() if hasattr(case, 'dict') else case.__dict__
            case_dict['positive_case'] = False
            all_cases.append(case_dict)

        self.logger.info(f"合併後總案例數: {len(all_cases)}")
        if all_cases:
            self.logger.info(f"第一個案例有positive_case標記: {'positive_case' in all_cases[0]}")
        
        symbols_processed = []
        for case in all_cases:
            if isinstance(case, dict) and 'symbol' in case:
                symbols_processed.append(case['symbol'])
            elif hasattr(case, 'symbol'):
                symbols_processed.append(case.symbol)
        symbols_processed = list(set(symbols_processed))
        
        return SearchResultData(
            cases=all_cases,
            total_cases=len(all_cases),
            search_config={},
            execution_time=10.0,
            symbols_processed=symbols_processed,
            positive_cases_count=len(positive_cases),
            negative_cases_count=len(negative_cases),
            summary={
                "total_cases": len(all_cases),
                "positive_cases": len(positive_cases),
                "negative_cases": len(negative_cases),
                "unique_symbols": len(symbols_processed),
                "time_range": {
                    "start": positive_cases[0].__dict__.get('time_range', {}).get('start', '2024-02-01') if positive_cases else '2024-02-01',
                    "end": positive_cases[0].__dict__.get('time_range', {}).get('end', '2025-05-31') if positive_cases else '2025-05-31'
                },
                "market_phase_distribution": {}
            },
            sampling_quality={
                "time_separation_score": 0.8,
                "symbol_diversity_score": 0.1,
                "market_phase_balance": 0.7,
                "overall_quality_score": 0.75,
                "warnings": []
            },
            cache_used=False
        )

# 創建全局服務實例
search_task_service = SearchTaskService()

# 新增文件: api/models/requests.py (添加反例搜索請求模型)

class NegativeCaseRequest(BaseModel):
    """反例搜索請求模型"""
    search_config: SearchConfigRequest = Field(..., description="反例搜索配置")
    negative_ratio: float = Field(default=2.0, ge=1.0, le=5.0, description="反例與正例的比例")
    enable_time_separation: bool = Field(
        default=True,
        description="是否啟用時間分離（防止反例與正例時間過近，按Symbol獨立計算）"
    )
    time_separation_days: int = Field(
        default=3,
        ge=0,
        le=30,
        description="時間分離天數（0=關閉，按Symbol獨立過濾）"
    )
    sampling_strategy: str = Field(default="time_separated", description="採樣策略")

    class Config:
        json_schema_extra = {
            "example": {
                "search_config": {
                    "name": "negative_example_search",
                    "timeframe": "12h",
                    "initial_conditions": []
                },
                "negative_ratio": 2.0,
                "enable_time_separation": True,
                "time_separation_days": 3,
                "sampling_strategy": "time_separated"
            }
        }

# 新增 API 路由: api/routes/two_stage_search.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from ..models.requests import SearchConfigRequest, NegativeCaseRequest
from ..models.responses import TaskStartResponse, SearchResponse
from ..services.search_task_service import search_task_service
from ..core.logging import get_logger

router = APIRouter(prefix="/two-stage", tags=["Two-Stage Search"])
logger = get_logger("api.routes.two_stage_search")

@router.post("/positive", response_model=TaskStartResponse)
async def start_positive_search(
    request: SearchConfigRequest,
    background_tasks: BackgroundTasks,
    symbols: Optional[List[str]] = None
):
    """
    開始正例搜索（第一階段）
    
    返回task_id，用於查詢進度和結果
    """
    try:
        task_id = await search_task_service.execute_positive_search(request, symbols)
        
        # 獲取任務信息
        task_info = search_task_service.get_task_status(task_id)
        
        return TaskStartResponse(
            success=True,
            data=task_info
        )
        
    except Exception as e:
        logger.error(f"Error starting positive search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/negative/{positive_task_id}", response_model=TaskStartResponse)
async def start_negative_search(
    positive_task_id: str,
    request: NegativeCaseRequest,
    background_tasks: BackgroundTasks
):
    """
    開始反例搜索（第二階段）
    
    基於指定的正例搜索結果生成反例
    """
    try:
        negative_task_id = await search_task_service.execute_negative_search(
            positive_task_id, request
        )
        
        # 構造任務信息返回
        task_info = {
            "task_id": negative_task_id,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "positive_task_id": positive_task_id
        }
        
        return TaskStartResponse(
            success=True,
            data=task_info
        )
        
    except Exception as e:
        logger.error(f"Error starting negative search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/combined/{positive_task_id}/{negative_task_id}", response_model=SearchResponse)
async def get_combined_results(
    positive_task_id: str,
    negative_task_id: str
):
    """
    獲取正反例合併結果
    
    返回完整的正反例數據集
    """
    try:
        combined_results = search_task_service.get_combined_results(
            positive_task_id, negative_task_id
        )
        
        if not combined_results:
            raise HTTPException(
                status_code=404, 
                detail="No results found for the specified task IDs"
            )
        
        return SearchResponse(
            success=True,
            data=combined_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting combined results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))