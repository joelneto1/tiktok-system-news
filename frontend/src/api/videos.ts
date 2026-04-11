import apiClient from './client'

export interface Video {
  id: string
  topic: string
  language: string
  model_type: string
  status: string
  duration: number | null
  file_size: number | null
  thumbnail_path: string | null
  created_at: string
  updated_at: string
  error: string | null
}

export interface ListVideosResponse {
  videos: Video[]
  total: number
  page: number
  page_size: number
}

export interface VideoScript {
  video_id: string
  script: string
  scenes: unknown[]
}

export async function listVideos(
  page?: number,
  pageSize?: number,
  status?: string,
): Promise<ListVideosResponse> {
  const params: Record<string, string | number> = {}
  if (page !== undefined) params.page = page
  if (pageSize !== undefined) params.page_size = pageSize
  if (status) params.status = status
  const { data } = await apiClient.get<ListVideosResponse>('/videos', { params })
  return data
}

export async function getVideo(id: string): Promise<Video> {
  const { data } = await apiClient.get<Video>(`/videos/${id}`)
  return data
}

export async function deleteVideo(id: string): Promise<void> {
  await apiClient.delete(`/videos/${id}`)
}

export function getVideoDownloadUrl(id: string): string {
  return `/api/videos/${id}/download`
}

export async function getVideoScript(id: string): Promise<VideoScript> {
  const { data } = await apiClient.get<VideoScript>(`/videos/${id}/script`)
  return data
}
