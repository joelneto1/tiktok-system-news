import apiClient from './client'

export interface Voice {
  voice_id: string
  name: string
  language: string
  gender: string
  accent: string
  preview_url: string
}

export interface ListVoicesResponse {
  voices: Voice[]
}

export async function listVoices(language?: string, category?: string): Promise<ListVoicesResponse> {
  const params: Record<string, string> = {}
  if (language) params.language = language
  if (category) params.category = category
  const { data } = await apiClient.get<ListVoicesResponse>('/voices', { params })
  return data
}
