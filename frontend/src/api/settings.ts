import apiClient from './client'

export interface Setting {
  id: string
  key: string
  value: string
  is_encrypted: boolean
  category: string
}

export async function listSettings(category?: string): Promise<Setting[]> {
  const params: Record<string, string> = {}
  if (category) params.category = category
  const { data } = await apiClient.get('/settings/', { params })
  // Backend returns array directly, not { settings: [] }
  return Array.isArray(data) ? data : data.settings || []
}

export async function updateSetting(key: string, value: string): Promise<Setting> {
  const { data } = await apiClient.put<Setting>(`/settings/${key}`, { value })
  return data
}

export async function bulkUpdateSettings(settings: Record<string, string>): Promise<Setting[]> {
  const { data } = await apiClient.put('/settings/bulk', { settings })
  return Array.isArray(data) ? data : []
}

export async function testSetting(key: string): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post(`/settings/${key}/test`)
  // Backend returns { status: "ok", message: "..." } or { status: "error", message: "..." }
  return {
    success: data.status === 'ok',
    message: data.message || (data.status === 'ok' ? 'Conexao OK!' : 'Falha na conexao'),
  }
}
