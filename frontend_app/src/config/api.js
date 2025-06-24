// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || API_BASE_URL.replace(/^http/, 'ws');
export const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || 'development';

// Construct full API and WebSocket URLs
export const API_URL = `${API_BASE_URL}/v1`;
export const WS_URL = `${WS_BASE_URL}/v1`;

// Helper to get WebSocket URL for a specific recipe
export const getRecipeWebSocketUrl = (recipeId, token) => {
  return `${WS_URL}/chat/${recipeId}?token=${token}`;
};

// Helper to check if we're in production
export const isProduction = () => ENVIRONMENT === 'production';