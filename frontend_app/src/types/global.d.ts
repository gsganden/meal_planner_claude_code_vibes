// Global type definitions

// Vite environment variables
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_WS_URL: string;
  readonly VITE_ENVIRONMENT: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Module declarations for JS files
declare module '../config/api' {
  export const API_BASE_URL: string;
  export const WS_BASE_URL: string;
  export const ENVIRONMENT: string;
  export const API_URL: string;
  export const WS_URL: string;
  export function getRecipeWebSocketUrl(recipeId: string, token: string): string;
  export function isProduction(): boolean;
}

declare module '../stores/authStore' {
  interface AuthStore {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: any | null;
    error: string | null;
    initialize: () => void;
    signup: (email: string, password: string, confirmPassword: string) => Promise<{ success: boolean; error?: string }>;
    signin: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
    logout: () => Promise<void>;
    clearError: () => void;
  }
  
  export const useAuthStore: () => AuthStore;
}