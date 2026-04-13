import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
})

// Auto-detect Content-Type: JSON for objects, multipart for FormData
apiClient.interceptors.request.use((config) => {
  if (!(config.data instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
  }
  return config
})

// JWT interceptor — attach token from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 handler — DON'T auto-redirect to login
// Just reject the promise and let each page handle it gracefully
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't auto-redirect — it causes login loops
    // Pages will show empty state on 401, AuthContext handles session expiry
    return Promise.reject(error)
  },
)

export default apiClient
