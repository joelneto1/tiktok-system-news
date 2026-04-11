import apiClient from './client'

export interface LogEntry {
  id: string
  job_id: string | null
  stage: string | null
  level: string
  message: string
  timestamp: string
}

export interface ListLogsParams {
  page?: number
  page_size?: number
  job_id?: string
  level?: string
  search?: string
}

export interface ListLogsResponse {
  logs: LogEntry[]
  total: number
  page: number
  page_size: number
}

export async function listLogs(params: ListLogsParams): Promise<ListLogsResponse> {
  const query: Record<string, string | number> = {}
  if (params.page !== undefined) query.page = params.page
  if (params.page_size !== undefined) query.page_size = params.page_size
  if (params.job_id) query.job_id = params.job_id
  if (params.level) query.level = params.level
  if (params.search) query.search = params.search
  const { data } = await apiClient.get<ListLogsResponse>('/logs/', { params: query })
  return data
}
