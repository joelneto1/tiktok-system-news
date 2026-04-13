import apiClient from './client'

export interface SoundEffect {
  id: string
  name: string
  sfx_type: string
  original_filename: string
  minio_path: string
  duration: number | null
  file_size: number | null
  mime_type: string
  created_at: string
}

export async function uploadSfx(file: File, name: string, sfxType: string): Promise<SoundEffect> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('name', name)
  formData.append('sfx_type', sfxType)
  const { data } = await apiClient.post<SoundEffect>('/sfx/upload', formData)
  return data
}

export async function listSfx(): Promise<{ sfx: SoundEffect[]; total: number }> {
  const { data } = await apiClient.get('/sfx/')
  return data
}

export async function deleteSfx(id: string): Promise<void> {
  await apiClient.delete(`/sfx/${id}`)
}

export function getSfxDownloadUrl(id: string): string {
  return `/api/sfx/${id}/download`
}
