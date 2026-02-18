import type {
  ExecutionOptimizationConfig,
  HyperparamOptimizationConfig,
  OptimizationConfigResponse,
  OptimizationResult,
  OptimizationTaskCreateResponse,
  OptimizationTaskStatusResponse,
  TaskType,
} from '@/lib/types/optimization'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = payload?.detail || payload?.error?.message || detail
    } catch {
      // ignore json parse failure
    }
    throw new Error(detail)
  }
  return response.json()
}

export async function startHyperparamOptimization(
  config: HyperparamOptimizationConfig
): Promise<OptimizationTaskCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/hyperparameter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })

  return parseResponse<OptimizationTaskCreateResponse>(response)
}

export async function startExecutionOptimization(
  config: ExecutionOptimizationConfig
): Promise<OptimizationTaskCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/execution`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })

  return parseResponse<OptimizationTaskCreateResponse>(response)
}

export async function getOptimizationResult(taskId: string): Promise<OptimizationResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/${taskId}/result`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  })

  return parseResponse<OptimizationResult>(response)
}

export async function getOptimizationConfig(): Promise<OptimizationConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/config`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  })

  return parseResponse<OptimizationConfigResponse>(response)
}

export async function getOptimizationTaskStatus(taskId: string): Promise<OptimizationTaskStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  })

  return parseResponse<OptimizationTaskStatusResponse>(response)
}

export async function exportOptimizationResult(
  taskType: TaskType,
  taskId: string,
  format: 'json' | 'csv'
): Promise<Blob | Record<string, unknown>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/${taskType}/${taskId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ format }),
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const payload = await response.json()
      detail = payload?.detail || payload?.error?.message || detail
    } catch {
      // ignore json parse failure
    }
    throw new Error(detail)
  }

  if (format === 'csv') {
    return response.blob()
  }

  return response.json()
}
