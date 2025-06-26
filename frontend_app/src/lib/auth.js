import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function getAccessToken() {
  return localStorage.getItem('access_token');
}

export function setAccessToken(token) {
  localStorage.setItem('access_token', token);
}

export function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

export function setRefreshToken(token) {
  localStorage.setItem('refresh_token', token);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

export async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await axios.post(`${API_URL}/v1/auth/refresh`, {
      refresh_token: refreshToken
    });

    const { access_token, refresh_token: newRefreshToken } = response.data;
    
    setAccessToken(access_token);
    if (newRefreshToken) {
      setRefreshToken(newRefreshToken);
    }

    return access_token;
  } catch (error) {
    // Clear tokens on refresh failure
    clearTokens();
    throw error;
  }
}

export function isAuthenticated() {
  return !!getAccessToken();
}

// Axios interceptor to add auth header
axios.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Axios interceptor to handle 401 errors
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await refreshAccessToken();
        return axios(originalRequest);
      } catch (refreshError) {
        // Redirect to login or emit auth error event
        window.location.href = '/signin';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);