import { createContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { loginApi, registerApi, getMeApi } from '@/api/auth'

export interface User {
  id: string
  email: string
  name: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  })

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const storedUser = localStorage.getItem('user')

    if (token && storedUser) {
      try {
        // Check if token is expired by reading JWT payload
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
        const isExpired = payload.exp && payload.exp * 1000 < Date.now()

        if (isExpired) {
          // Token expired — clear session
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
        } else {
          // Token valid — restore session
          const user = JSON.parse(storedUser) as User
          setState({ user, token, isAuthenticated: true, isLoading: false })
        }
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setState((s) => ({ ...s, isLoading: false }))
      }
    } else {
      setState((s) => ({ ...s, isLoading: false }))
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginApi(email, password)

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))

    setState({
      user: data.user,
      token: data.access_token,
      isAuthenticated: true,
      isLoading: false,
    })
  }, [])

  const register = useCallback(async (name: string, email: string, password: string) => {
    const data = await registerApi(email, password, name)

    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))

    setState({
      user: data.user,
      token: data.access_token,
      isAuthenticated: true,
      isLoading: false,
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setState({ user: null, token: null, isAuthenticated: false, isLoading: false })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
