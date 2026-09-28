// forecast-api 的类型与请求封装。该服务是 Python(FastAPI) 实现，不走 goctl
// 生成，这里手写类型与后端 app/schemas.py + app/ml/*.py 的输出保持一致。
import { request } from './client'

export type ForecastJobKind = 'univariate' | 'multivariate'
export type ForecastJobStatus = 'queued' | 'running' | 'done' | 'failed'

export interface ForecastJobCreateReq {
  kind: ForecastJobKind
  epochs?: number
}

export interface ForecastJobSummary {
  id: string
  kind: ForecastJobKind
  params: { epochs: number | null }
  owner: string
  status: ForecastJobStatus
  progress: string
  error: string | null
  created_at: number
  started_at: number | null
  finished_at: number | null
  has_result: boolean
}

export interface ComparisonCheck {
  actual: number | null
  reference: number | null
  delta: number | null
  within_tolerance: boolean
}

export interface UnivariateComparison {
  reference_source: string
  epochs_match: boolean
  checks: Record<string, ComparisonCheck>
  passed: boolean
}

export interface MultivariateComparison {
  reference_source: string
  epochs_match: boolean
  modes: Record<string, { checks: Record<string, ComparisonCheck>; passed: boolean }>
  passed: boolean
}

export interface UnivariateMetrics {
  device: string
  seed: number
  params: number
  train_samples: number
  test_samples: number
  train_mse_scaled: number
  test_mse_scaled: number
  train_seconds: number
  model_inverse: { MAE: number; RMSE: number; R2: number }
  persistence_inverse: { MAE: number; RMSE: number; R2: number }
  residual: { mean: number; std: number }
}

export interface UnivariateResult {
  kind: 'univariate'
  seed: number
  epochs: number
  device: string
  torch_version: string
  metrics: UnivariateMetrics
  series: {
    raw: { t: number[]; value: number[] }
    loss: { epoch: number[]; train: number[]; test: number[] }
    prediction: { sample: number[]; true: number[]; pred: number[] }
    residual_histogram: { bin_left: number[]; bin_right: number[]; counts: number[] }
    scatter: { actual: number[]; predicted: number[] }
  }
  comparison: UnivariateComparison
}

export interface MultivariateMethodStats {
  val_alarm_rate: number
  benign_alarm_rate: number
  fault_alarm_rate: number
  detection_delay: number | null
}

export interface MultivariateModeResult {
  metrics: {
    b_marginal: {
      pre_mean: number
      post_mean: number
      pre_std: number
      post_std: number
    }
    corr_a_b: { train: number; benign: number; post_onset: number }
    methods: Record<string, MultivariateMethodStats>
  }
  thresholds: Record<string, number>
  series: {
    channels: { t: number[]; a: number[]; b: number[] }
    scores: {
      t: number[]
      mv: (number | null)[]
      uv_b: (number | null)[]
      uv_a: (number | null)[]
      ewma_a: (number | null)[]
      ewma_b: (number | null)[]
    }
    coupling: {
      train: { a: number[]; b: number[] }
      post: { a: number[]; b: number[] }
    }
  }
}

export interface MultivariateResult {
  kind: 'multivariate'
  seed: number
  epochs: number
  device: string
  torch_version: string
  constants: {
    benign_start: number
    fault_onset: number
    ramp: number
    lag_max: number
    val_start: number
    smooth: number
    quantile: number
    ewma_lambda: number
  }
  modes: Record<string, MultivariateModeResult>
  comparison: MultivariateComparison
}

export type ForecastResult = UnivariateResult | MultivariateResult

export type ForecastJobDetail = ForecastJobSummary & { result: ForecastResult | null }

// Route paths mirror forecast-api routes; the gateway strips the /api prefix.
export function createForecastJob(req: ForecastJobCreateReq): Promise<ForecastJobSummary> {
  return request<ForecastJobSummary>('POST', '/forecast/jobs', req)
}

export function listForecastJobs(): Promise<{ jobs: ForecastJobSummary[] }> {
  return request<{ jobs: ForecastJobSummary[] }>('GET', '/forecast/jobs')
}

export function getForecastJob(id: string): Promise<ForecastJobDetail> {
  return request<ForecastJobDetail>('GET', `/forecast/jobs/${id}`)
}

export function deleteForecastJob(id: string): Promise<null> {
  return request<null>('DELETE', `/forecast/jobs/${id}`)
}
