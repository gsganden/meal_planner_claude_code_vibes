import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function AuthPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [validationErrors, setValidationErrors] = useState({})

  const { signin, signup, error, clearError, isAuthenticated } = useAuthStore()

  // Set mode based on URL
  useEffect(() => {
    const path = location.pathname
    if (path.includes('signup')) {
      setMode('signup')
    } else {
      setMode('signin')
    }
  }, [location])

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/')
    }
  }, [isAuthenticated, navigate])

  // Clear error when switching modes
  useEffect(() => {
    clearError()
    setValidationErrors({})
  }, [mode, clearError])

  // Validate email
  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return re.test(email)
  }

  // Validate password
  const validatePassword = (password) => {
    const hasLetter = /[a-zA-Z]/.test(password)
    const hasNumber = /[0-9]/.test(password)
    return password.length >= 8 && hasLetter && hasNumber
  }

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Clear previous errors
    setValidationErrors({})
    clearError()

    // Validate
    const errors = {}
    if (!validateEmail(email)) {
      errors.email = 'Please enter a valid email address'
    }
    if (!validatePassword(password)) {
      errors.password = 'Password must be at least 8 characters with letters and numbers'
    }
    if (mode === 'signup' && password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match'
    }

    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors)
      return
    }

    // Submit
    setIsLoading(true)
    try {
      let result
      if (mode === 'signup') {
        result = await signup(email, password, confirmPassword)
      } else {
        result = await signin(email, password)
      }
      
      if (result.success) {
        navigate('/')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // Check if form is valid
  const isFormValid = () => {
    if (!email || !password) return false
    if (mode === 'signup' && !confirmPassword) return false
    if (!validateEmail(email)) return false
    if (!validatePassword(password)) return false
    if (mode === 'signup' && password !== confirmPassword) return false
    return true
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h1 className="text-center text-3xl font-bold text-gray-900">
            Recipe Chat Assistant
          </h1>
          <h2 className="mt-6 text-center text-2xl font-semibold text-gray-900">
            {mode === 'signin' ? 'Sign in to your account' : 'Create a new account'}
          </h2>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => {
                  if (email && !validateEmail(email)) {
                    setValidationErrors({ ...validationErrors, email: 'Please enter a valid email address' })
                  } else {
                    const { email: _, ...rest } = validationErrors
                    setValidationErrors(rest)
                  }
                }}
                className={`mt-1 block w-full px-3 py-2 border ${
                  validationErrors.email ? 'border-red-300' : 'border-gray-300'
                } rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500`}
              />
              {validationErrors.email && (
                <p className="mt-1 text-sm text-red-600">{validationErrors.email}</p>
              )}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`mt-1 block w-full px-3 py-2 border ${
                  validationErrors.password ? 'border-red-300' : 'border-gray-300'
                } rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500`}
              />
              {validationErrors.password && (
                <p className="mt-1 text-sm text-red-600">{validationErrors.password}</p>
              )}
              {mode === 'signup' && password && (
                <div className="mt-2 space-y-1">
                  <div className={`text-xs ${password.length >= 8 ? 'text-green-600' : 'text-gray-400'}`}>
                    ✓ At least 8 characters
                  </div>
                  <div className={`text-xs ${/[a-zA-Z]/.test(password) ? 'text-green-600' : 'text-gray-400'}`}>
                    ✓ Contains letters
                  </div>
                  <div className={`text-xs ${/[0-9]/.test(password) ? 'text-green-600' : 'text-gray-400'}`}>
                    ✓ Contains numbers
                  </div>
                </div>
              )}
            </div>

            {mode === 'signup' && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`mt-1 block w-full px-3 py-2 border ${
                    validationErrors.confirmPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500`}
                />
                {validationErrors.confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">{validationErrors.confirmPassword}</p>
                )}
                {confirmPassword && password !== confirmPassword && (
                  <p className="mt-1 text-sm text-red-600">Passwords do not match</p>
                )}
              </div>
            )}
          </div>

          <div>
            <button
              type="submit"
              disabled={!isFormValid() || isLoading}
              className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                isFormValid() && !isLoading
                  ? 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                  : 'bg-gray-400 cursor-not-allowed'
              }`}
            >
              {isLoading ? 'Please wait...' : mode === 'signin' ? 'Sign in' : 'Sign up'}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setMode(mode === 'signin' ? 'signup' : 'signin')
                navigate(mode === 'signin' ? '/auth/signup' : '/auth/signin')
                // Clear passwords when switching
                setPassword('')
                setConfirmPassword('')
              }}
              className="text-sm text-blue-600 hover:text-blue-500"
            >
              {mode === 'signin'
                ? "Don't have an account? Sign up"
                : 'Already have an account? Sign in'}
            </button>
          </div>

          {mode === 'signin' && (
            <div className="text-center">
              <button
                type="button"
                onClick={() => navigate('/auth/forgot-password')}
                className="text-sm text-gray-600 hover:text-gray-500"
              >
                Forgot your password?
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}