import apiClient from './client'

export interface SystemPrompt {
  id: string
  key: string
  name: string
  description: string | null
  content: string
  model_type: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreatePromptData {
  key: string
  name: string
  description?: string
  content: string
  model_type?: string
}

export async function listPrompts(modelType?: string): Promise<SystemPrompt[]> {
  const params: Record<string, string> = {}
  if (modelType) params.model_type = modelType
  const { data } = await apiClient.get<SystemPrompt[]>('/prompts/', { params })
  return data
}

export async function updatePrompt(key: string, content: string): Promise<SystemPrompt> {
  const { data } = await apiClient.put<SystemPrompt>(`/prompts/${key}`, { content })
  return data
}

export async function createPrompt(promptData: CreatePromptData): Promise<SystemPrompt> {
  const { data } = await apiClient.post<SystemPrompt>('/prompts', promptData)
  return data
}

export async function deletePrompt(key: string): Promise<void> {
  await apiClient.delete(`/prompts/${key}`)
}
