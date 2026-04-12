import apiClient from './client'

export interface PipelineStartRequest {
  topic: string
  language: string
  model_type: string
  reference_id?: string
  audio_id?: string
  voice_id?: string
}

export interface PipelineStartResponse {
  video_id: string
  status: string
  message: string
}

export interface StageInfo {
  name: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  started_at: string | null
  completed_at: string | null
}

export interface VideoDetail {
  id: string
  topic: string
  language: string
  model_type: string
  status: string
  current_stage: string | null
  progress_percent: number
  total_stages: number
  completed_stages: number
  attempts: number
  script: string | null
  output_url: string | null
  error_message: string | null
  reference_id: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface PipelineStatusResponse {
  video: VideoDetail
  stages: StageInfo[]
}

export async function startPipeline(data: PipelineStartRequest): Promise<PipelineStartResponse> {
  const { data: resp } = await apiClient.post<PipelineStartResponse>('/pipeline/start', data)
  return resp
}

export async function enqueuePipeline(data: PipelineStartRequest): Promise<PipelineStartResponse> {
  const { data: resp } = await apiClient.post<PipelineStartResponse>('/pipeline/enqueue', data)
  return resp
}

export async function getPipelineStatus(videoId: string): Promise<PipelineStatusResponse> {
  const { data } = await apiClient.get<PipelineStatusResponse>(`/pipeline/${videoId}/status`)
  return data
}

export async function retryPipeline(videoId: string): Promise<void> {
  await apiClient.post(`/pipeline/${videoId}/retry`)
}
