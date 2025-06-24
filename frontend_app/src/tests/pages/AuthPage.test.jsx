import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import AuthPage from '../../pages/AuthPage'
import { useAuthStore } from '../../stores/authStore'

// Mock the auth store
vi.mock('../../stores/authStore')

// Mock axios
vi.mock('axios', () => ({
  default: {
    defaults: { baseURL: '' },
    post: vi.fn(),
    create: vi.fn(() => ({
      post: vi.fn(),
      defaults: { baseURL: '' },
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

const renderAuthPage = (route = '/signin') => {
  window.history.pushState({}, 'Test page', route)
  return render(
    <BrowserRouter>
      <AuthPage />
    </BrowserRouter>
  )
}

describe('AuthPage - UC0.0: User Authentication', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue({
      isAuthenticated: false,
      error: null,
      signin: vi.fn(),
      signup: vi.fn(),
      clearError: vi.fn(),
    })
  })

  describe('UC0.0.1: New User Account Creation (Sign Up)', () => {
    it('should display signin form by default and allow switching to signup', async () => {
      renderAuthPage()
      
      // Verify signin form is shown by default
      expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.queryByLabelText(/confirm password/i)).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      
      // Click signup link
      const signupLink = screen.getByText(/don't have an account\? sign up/i)
      await userEvent.click(signupLink)
      
      // Verify signup form is shown
      expect(screen.getByText(/create a new account/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument()
    })

    it('should validate email format on blur', async () => {
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      const emailInput = screen.getByLabelText(/email/i)
      
      // Enter invalid email
      await userEvent.type(emailInput, 'invalid-email')
      await userEvent.tab()
      
      // Should show error
      expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
      
      // Enter valid email
      await userEvent.clear(emailInput)
      await userEvent.type(emailInput, 'test@example.com')
      await userEvent.tab()
      
      // Error should disappear
      expect(screen.queryByText(/please enter a valid email address/i)).not.toBeInTheDocument()
    })

    it('should validate password requirements', async () => {
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      const passwordInput = screen.getByLabelText(/^password$/i)
      
      // Test too short password
      await userEvent.type(passwordInput, 'short')
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
      
      // Test password without number
      await userEvent.clear(passwordInput)
      await userEvent.type(passwordInput, 'longpassword')
      // Check that "Contains numbers" is not green (gray-400)
      const containsNumbers = screen.getByText('✓ Contains numbers')
      expect(containsNumbers).toHaveClass('text-gray-400')
      
      // Test valid password
      await userEvent.clear(passwordInput)
      await userEvent.type(passwordInput, 'password123')
      // All requirements should be green
      expect(screen.getByText('✓ At least 8 characters')).toHaveClass('text-green-600')
      expect(screen.getByText('✓ Contains letters')).toHaveClass('text-green-600')
      expect(screen.getByText('✓ Contains numbers')).toHaveClass('text-green-600')
    })

    it('should validate password confirmation matches', async () => {
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)
      
      await userEvent.type(passwordInput, 'password123')
      await userEvent.type(confirmInput, 'password456')
      
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      
      await userEvent.clear(confirmInput)
      await userEvent.type(confirmInput, 'password123')
      
      expect(screen.queryByText(/passwords do not match/i)).not.toBeInTheDocument()
    })

    it('should keep submit button disabled until form is valid', async () => {
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      const submitButton = screen.getByRole('button', { name: /sign up/i })
      expect(submitButton).toBeDisabled()
      
      // Fill in valid form
      await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com')
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123')
      await userEvent.type(screen.getByLabelText(/confirm password/i), 'password123')
      
      expect(submitButton).toBeEnabled()
    })

    it('should handle successful signup', async () => {
      const mockSignup = vi.fn().mockResolvedValue({ success: true })
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: null,
        signup: mockSignup,
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      // Fill form
      await userEvent.type(screen.getByLabelText(/email/i), 'newuser@example.com')
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123')
      await userEvent.type(screen.getByLabelText(/confirm password/i), 'password123')
      
      // Submit
      const submitButton = screen.getByRole('button', { name: /sign up/i })
      await userEvent.click(submitButton)
      
      // Verify the signup was called with correct arguments
      
      await waitFor(() => {
        expect(mockSignup).toHaveBeenCalledWith(
          'newuser@example.com',
          'password123',
          'password123'
        )
      })
    })

    it('should handle duplicate email error', async () => {
      const mockSignup = vi.fn().mockResolvedValue({ success: false, error: 'Email already exists' })
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: 'An account with this email already exists. Try signing in instead.',
        signup: mockSignup,
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      // Fill and submit form
      await userEvent.type(screen.getByLabelText(/email/i), 'existing@example.com')
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123')
      await userEvent.type(screen.getByLabelText(/confirm password/i), 'password123')
      await userEvent.click(screen.getByRole('button', { name: /sign up/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/an account with this email already exists/i)).toBeInTheDocument()
      })
    })
  })

  describe('UC0.0.2: Existing User Authentication (Sign In)', () => {
    it('should display signin form by default', () => {
      renderAuthPage()
      
      expect(screen.getByText(/sign in to your account/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should handle successful signin', async () => {
      const mockSignin = vi.fn().mockResolvedValue({ success: true })
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: null,
        signin: mockSignin,
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      
      await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'password123')
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await userEvent.click(submitButton)
      
      await waitFor(() => {
        expect(mockSignin).toHaveBeenCalledWith(
          'user@example.com',
          'password123'
        )
      })
    })

    it('should handle invalid credentials error', async () => {
      const mockSignin = vi.fn().mockResolvedValue({ success: false, error: 'Invalid credentials' })
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: 'Invalid email or password',
        signin: mockSignin,
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      
      await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword')
      await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })
    })
  })

  describe('UC0.0.3: Form Mode Switching', () => {
    it('should preserve email when switching between signin and signup', async () => {
      renderAuthPage()
      
      // Enter email in signin form
      const emailInput = screen.getByLabelText(/email/i)
      await userEvent.type(emailInput, 'test@example.com')
      
      // Switch to signup
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      // Email should be preserved
      expect(screen.getByLabelText(/email/i)).toHaveValue('test@example.com')
      
      // Switch back to signin
      await userEvent.click(screen.getByText(/already have an account\? sign in/i))
      
      // Email should still be preserved
      expect(screen.getByLabelText(/email/i)).toHaveValue('test@example.com')
    })

    it('should clear passwords when switching modes', async () => {
      renderAuthPage()
      
      // Enter password in signin form
      await userEvent.type(screen.getByLabelText(/password/i), 'password123')
      
      // Switch to signup
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      // Password should be cleared
      expect(screen.getByLabelText(/^password$/i)).toHaveValue('')
      expect(screen.getByLabelText(/confirm password/i)).toHaveValue('')
    })

    it('should clear errors when switching modes', async () => {
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: 'Invalid email or password',
        signin: vi.fn(),
        signup: vi.fn(),
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      
      // Error should be visible
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      
      // Switch to signup
      await userEvent.click(screen.getByText(/don't have an account\? sign up/i))
      
      // clearError should have been called
      expect(useAuthStore().clearError).toHaveBeenCalled()
    })
  })

  describe('UC0.0.7: Loading States', () => {
    it('should show loading state during authentication', async () => {
      const mockSignin = vi.fn().mockImplementation(() => new Promise(() => {})) // Never resolves
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: null,
        signin: mockSignin,
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      
      await userEvent.type(screen.getByLabelText(/email/i), 'user@example.com')
      await userEvent.type(screen.getByLabelText(/password/i), 'password123')
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await userEvent.click(submitButton)
      
      // Button should show loading state and be disabled
      await waitFor(() => {
        expect(submitButton).toHaveTextContent('Please wait...')
      })
      expect(submitButton).toBeDisabled()
    })
  })

  describe('UC0.0.9: Error Message Behavior', () => {
    it('should display network error messages', async () => {
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: 'Unable to connect. Please check your connection and try again.',
        signin: vi.fn(),
        signup: vi.fn(),
        clearError: vi.fn(),
      })
      
      renderAuthPage()
      
      expect(screen.getByText(/unable to connect/i)).toBeInTheDocument()
    })

    it('should clear error when user modifies form', async () => {
      const mockClearError = vi.fn()
      useAuthStore.mockReturnValue({
        isAuthenticated: false,
        error: 'Invalid email or password',
        signin: vi.fn(),
        signup: vi.fn(),
        clearError: mockClearError,
      })
      
      renderAuthPage()
      
      expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      
      // Type in email field
      await userEvent.type(screen.getByLabelText(/email/i), 'a')
      
      // Error should be cleared
      expect(mockClearError).toHaveBeenCalled()
    })
  })
})