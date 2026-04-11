import apiClient from './client'

export interface ConnectionAccount {
  id: string
  service: string
  account_name: string
  account_type: string | null
  proxy_url: string | null
  is_active: boolean
  credits: number
  cookie_expires_at: string | null
  token_expires_at: string | null
  status: string
  last_verified_at: string | null
  error_message: string | null
  created_at: string
}

export interface AddAccountData {
  service: string
  account_name: string
  account_type?: string | null
  cookies_json?: string | null
  proxy_url?: string | null
}

export interface UpdateAccountData {
  is_active?: boolean
  cookies_json?: string | null
  proxy_url?: string | null
  account_type?: string | null
}

export async function listAccounts(service?: string): Promise<ConnectionAccount[]> {
  const params: Record<string, string> = {}
  if (service) params.service = service
  const { data } = await apiClient.get<ConnectionAccount[]>('/connections/', { params })
  return data
}

export async function addAccount(accountData: AddAccountData): Promise<ConnectionAccount> {
  const { data } = await apiClient.post<ConnectionAccount>('/connections/', accountData)
  return data
}

export async function toggleAccount(id: string): Promise<ConnectionAccount> {
  const { data } = await apiClient.patch<ConnectionAccount>(`/connections/${id}/toggle`)
  return data
}

export async function updateAccount(id: string, accountData: UpdateAccountData): Promise<ConnectionAccount> {
  const { data } = await apiClient.patch<ConnectionAccount>(`/connections/${id}`, accountData)
  return data
}

export async function refreshAccount(id: string): Promise<{ status: string; last_verified_at: string }> {
  const { data } = await apiClient.post<{ status: string; last_verified_at: string }>(`/connections/${id}/refresh`)
  return data
}

export async function deleteAccount(id: string): Promise<void> {
  await apiClient.delete(`/connections/${id}`)
}
