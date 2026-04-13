import apiClient from './client'

export interface BackgroundAudio {
  id: string
  name: string
  original_filename: string
  minio_path: string
  duration: number | null
  file_size: number | null
  mime_type: string
  created_at: string
}

export async function uploadAudio(file: File, name?: string): Promise<BackgroundAudio> {
  const formData = new FormData()
  formData.append('file', file)
  if (name) formData.append('name', name)
  const { data } = await apiClient.post<BackgroundAudio>('/audios/upload', formData)
  return data
}

export async function listAudios(): Promise<{ audios: BackgroundAudio[]; total: number }> {
  const { data } = await apiClient.get('/audios/')
  return data
}

export async function renameAudio(id: string, name: string): Promise<BackgroundAudio> {
  const formData = new FormData()
  formData.append('name', name)
  const { data } = await apiClient.patch<BackgroundAudio>(`/audios/${id}/rename`, formData)
  return data
}

export async function deleteAudio(id: string): Promise<void> {
  await apiClient.delete(`/audios/${id}`)
}

export function getAudioDownloadUrl(id: string): string {
  return `/api/audios/${id}/download`
}
