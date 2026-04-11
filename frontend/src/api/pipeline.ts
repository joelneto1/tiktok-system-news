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

export interface PipelineStatus {
  video_id: string
  status: string
  stage: string | null
  progress: number | null
  error: string | null
}

export async function startPipeline(data: PipelineStartRequest): Promise<PipelineStartResponse> {
  const { data: resp } = await apiClient.post<PipelineStartResponse>('/pipeline/start', data)
  return resp
}

export async function enqueuePipeline(data: PipelineStartRequest): Promise<PipelineStartResponse> {
  const { data: resp } = await apiClient.post<PipelineStartResponse>('/pipeline/enqueue', data)
  return resp
}

export async function getPipelineStatus(videoId: string): Promise<PipelineStatus> {
  const { data } = await apiClient.get<PipelineStatus>(`/pipeline/status/${videoId}`)
  return data
}

export async function retryPipeline(videoId: string): Promise<void> {
  await apiClient.post(`/pipeline/${videoId}/retry`)
}
