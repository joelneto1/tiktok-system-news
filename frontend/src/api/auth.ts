import apiClient from './client'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user: {
    id: string
    email: string
    name: string
  }
}

function parseJwt(token: string): Record<string, string> {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return {}
  }
}

export async function loginApi(email: string, password: string): Promise<AuthResponse> {
  const { data: tokens } = await apiClient.post<TokenResponse>('/auth/login', { email, password })

  // Extract user info from JWT payload (no need to call /auth/me)
  const payload = parseJwt(tokens.access_token)

  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    user: {
      id: payload.sub || '',
      email: payload.email || email,
      name: payload.email || email,
    },
  }
}

export async function registerApi(email: string, password: string, username?: string): Promise<AuthResponse> {
  const { data: tokens } = await apiClient.post<TokenResponse>('/auth/register', {
    email,
    password,
    username,
  })

  const payload = parseJwt(tokens.access_token)

  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    user: {
      id: payload.sub || '',
      email: payload.email || email,
      name: username || payload.email || email,
    },
  }
}

export async function getMeApi(): Promise<{ id: string; email: string; name: string }> {
  const { data } = await apiClient.get('/auth/me')
  return {
    id: data.id,
    email: data.email,
    name: data.username || data.email,
  }
}

export async function refreshTokenApi(refreshToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}
