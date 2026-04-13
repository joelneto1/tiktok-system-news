import apiClient from './client'

export interface Reference {
  id: string
  name: string
  original_filename: string
  thumbnail_path: string | null
  duration: number | null
  file_size: number | null
  created_at: string
}

export interface ListReferencesResponse {
  references: Reference[]
  total: number
}

export async function uploadReference(file: File, name?: string): Promise<Reference> {
  const formData = new FormData()
  formData.append('file', file)
  if (name) {
    formData.append('name', name)
  }
  const { data } = await apiClient.post<Reference>('/references/upload', formData, {
    timeout: 120000, // 2 minutes for large video uploads
  })
  return data
}

export async function listReferences(): Promise<ListReferencesResponse> {
  const { data } = await apiClient.get<ListReferencesResponse>('/references/')
  return data
}

export async function renameReference(id: string, name: string): Promise<Reference> {
  const { data } = await apiClient.patch<Reference>(`/references/${id}`, { name })
  return data
}

export async function deleteReference(id: string): Promise<void> {
  await apiClient.delete(`/references/${id}`)
}

export function getReferenceThumbnailUrl(id: string): string {
  return `/api/references/${id}/thumbnail`
}

export function getReferenceDownloadUrl(id: string): string {
  return `/api/references/${id}/download`
}
