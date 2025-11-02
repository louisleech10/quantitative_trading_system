/**
 * useOptimization Hook - 優化任務管理與WebSocket訂閱
 *
 * 功能:
 * 1. 創建優化任務
 * 2. WebSocket實時訂閱（進度、最佳值、里程碑）
 * 3. 任務狀態查詢
 * 4. 自動重連機制
 *
 * Author: Claude (Phase 3.5 Day 5-6)
 * Date: 2025-11-02
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  OptimizationTaskInfo,
  OptimizationTaskStatus,
  CreateOptimizationTaskRequest,
  CreateOptimizationTaskResponse,
  TaskStatusResponse,
  WebSocketMessage,
  ProgressUpdateData,
  NewBestValueData,
  MilestoneReachedData
} from '@/types/optimization'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

// ==================== API Functions ====================

/**
 * 創建優化任務
 */
export async function createOptimizationTask(
  request: CreateOptimizationTaskRequest
): Promise<CreateOptimizationTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(request)
  })

  if (!response.ok) {
    throw new Error(`Failed to create optimization task: ${response.statusText}`)
  }

  return response.json()
}

/**
 * 啟動優化任務
 */
export async function startOptimizationTask(taskId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/start`,
    {
      method: 'POST'
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to start optimization task: ${response.statusText}`)
  }
}

/**
 * 獲取任務狀態
 */
export async function getOptimizationTask(taskId: string): Promise<OptimizationTaskInfo> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}`)

  if (!response.ok) {
    throw new Error(`Failed to get optimization task: ${response.statusText}`)
  }

  const data: TaskStatusResponse = await response.json()
  return data.data
}

/**
 * 取消優化任務
 */
export async function cancelOptimizationTask(taskId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/cancel`,
    {
      method: 'POST'
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to cancel optimization task: ${response.statusText}`)
  }
}

// ==================== useOptimization Hook ====================

export interface UseOptimizationOptions {
  taskId?: string
  autoConnect?: boolean
  onProgressUpdate?: (data: ProgressUpdateData) => void
  onNewBestValue?: (data: NewBestValueData) => void
  onMilestoneReached?: (data: MilestoneReachedData) => void
  onCompleted?: (taskInfo: OptimizationTaskInfo) => void
  onError?: (error: Error) => void
}

export function useOptimization(options: UseOptimizationOptions = {}) {
  const {
    taskId,
    autoConnect = true,
    onProgressUpdate,
    onNewBestValue,
    onMilestoneReached,
    onCompleted,
    onError
  } = options

  // State
  const [taskInfo, setTaskInfo] = useState<OptimizationTaskInfo | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Refs
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)

  // ==================== WebSocket ====================

  /**
   * 連接WebSocket
   */
  const connect = useCallback((targetTaskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[useOptimization] WebSocket already connected')
      return
    }

    try {
      const wsUrl = `${WS_BASE_URL}/ws/optimization/${targetTaskId}`
      console.log('[useOptimization] Connecting to:', wsUrl)

      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[useOptimization] WebSocket connected')
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          console.log('[useOptimization] Received:', message.event, message.data)

          switch (message.event) {
            case 'connected':
              // 連接成功
              break

            case 'task_status':
              // 當前任務狀態
              setTaskInfo(message.data)
              break

            case 'progress_update':
              // 進度更新
              setTaskInfo(prev =>
                prev
                  ? {
                      ...prev,
                      progress: {
                        ...prev.progress,
                        ...message.data
                      }
                    }
                  : null
              )
              onProgressUpdate?.(message.data)
              break

            case 'new_best_value':
              // 新最佳值
              setTaskInfo(prev =>
                prev
                  ? {
                      ...prev,
                      progress: {
                        ...prev.progress,
                        best_value: message.data.best_value,
                        best_params: message.data.best_params
                      }
                    }
                  : null
              )
              onNewBestValue?.(message.data)
              break

            case 'milestone_reached':
              // 里程碑達成
              setTaskInfo(prev =>
                prev
                  ? {
                      ...prev,
                      progress: {
                        ...prev.progress,
                        current_milestone: message.data.milestone_percentage
                      }
                    }
                  : null
              )
              onMilestoneReached?.(message.data)
              break

            case 'optimization_finished':
              // 優化完成
              setTaskInfo(prev =>
                prev
                  ? {
                      ...prev,
                      status: OptimizationTaskStatus.COMPLETED,
                      completed_at: new Date().toISOString(),
                      progress: {
                        ...prev.progress,
                        completion_percentage: 100
                      }
                    }
                  : null
              )
              onCompleted?.(message.data)
              break

            case 'ping':
              // 心跳
              ws.send(JSON.stringify({ type: 'pong' }))
              break

            case 'error':
              // 錯誤
              const err = new Error(message.data.message || 'Optimization error')
              setError(err)
              onError?.(err)
              break
          }
        } catch (err) {
          console.error('[useOptimization] Failed to parse message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('[useOptimization] WebSocket error:', event)
        const err = new Error('WebSocket connection error')
        setError(err)
        onError?.(err)
      }

      ws.onclose = () => {
        console.log('[useOptimization] WebSocket closed')
        setIsConnected(false)

        // 自動重連（最多5次）
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000)
          console.log(
            `[useOptimization] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/5)`
          )

          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connect(targetTaskId)
          }, delay)
        }
      }

      wsRef.current = ws
    } catch (err) {
      console.error('[useOptimization] Failed to connect:', err)
      const error = err instanceof Error ? err : new Error('Failed to connect')
      setError(error)
      onError?.(error)
    }
  }, [onProgressUpdate, onNewBestValue, onMilestoneReached, onCompleted, onError])

  /**
   * 斷開WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
  }, [])

  // ==================== Effects ====================

  /**
   * 自動連接（如果提供了taskId）
   */
  useEffect(() => {
    if (taskId && autoConnect) {
      connect(taskId)
    }

    return () => {
      disconnect()
    }
  }, [taskId, autoConnect, connect, disconnect])

  // ==================== Public API ====================

  return {
    // State
    taskInfo,
    isConnected,
    error,

    // Actions
    connect,
    disconnect,

    // API Helpers
    createTask: createOptimizationTask,
    startTask: startOptimizationTask,
    getTask: getOptimizationTask,
    cancelTask: cancelOptimizationTask
  }
}
