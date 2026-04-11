import apiClient from './client'

export interface StorageObject {
  name: string
  size: number
  is_dir: boolean
  last_modified: string
  content_type: string
}

export interface BrowseStorageResponse {
  objects: StorageObject[]
  prefix: string
}

export async function browseStorage(prefix?: string): Promise<BrowseStorageResponse> {
  const params: Record<string, string> = {}
  if (prefix) params.prefix = prefix
  const { data } = await apiClient.get<BrowseStorageResponse>('/storage/browse', { params })
  return data
}

export function getDownloadUrl(path: string): string {
  return `/api/storage/download?path=${encodeURIComponent(path)}`
}

export async function deleteStorageFile(path: string): Promise<void> {
  await apiClient.delete('/storage/file', { params: { path } })
}
