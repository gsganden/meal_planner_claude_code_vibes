import { create } from 'zustand'
import axios from 'axios'

// Configure axios defaults
// Don't set baseURL since Vite proxy handles /v1 routes
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token expiration
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post('/v1/auth/refresh', {
            refresh_token: refreshToken,
          })
          const { access_token, refresh_token: newRefreshToken } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', newRefreshToken)
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return axios(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        useAuthStore.getState().logout()
        window.location.href = '/auth/signin'
      }
    }
    return Promise.reject(error)
  }
)

export const useAuthStore = create((set) => ({
  isAuthenticated: false,
  isLoading: true,
  user: null,
  error: null,

  // Initialize auth state from localStorage
  initialize: () => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // TODO: Validate token with API
      set({ isAuthenticated: true, isLoading: false })
    } else {
      set({ isAuthenticated: false, isLoading: false })
    }
  },

  // Sign up
  signup: async (email, password, confirmPassword) => {
    try {
      set({ error: null })
      const response = await axios.post('/v1/auth/signup', {
        email,
        password,
        confirmPassword,
      })
      const { access_token, refresh_token, user } = response.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      set({ isAuthenticated: true, user, error: null })
      return { success: true }
    } catch (error) {
      const message = error.response?.data?.detail?.message || 'Signup failed'
      set({ error: message })
      return { success: false, error: message }
    }
  },

  // Sign in
  signin: async (email, password) => {
    try {
      set({ error: null })
      const response = await axios.post('/v1/auth/signin', {
        email,
        password,
      })
      const { access_token, refresh_token, user } = response.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      set({ isAuthenticated: true, user, error: null })
      return { success: true }
    } catch (error) {
      const message = error.response?.data?.detail?.message || 'Invalid email or password'
      set({ error: message })
      return { success: false, error: message }
    }
  },

  // Sign out
  logout: async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        await axios.post('/v1/auth/logout', { refresh_token: refreshToken })
      }
    } catch (error) {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ isAuthenticated: false, user: null, error: null })
    }
  },

  // Clear error
  clearError: () => set({ error: null }),
}))