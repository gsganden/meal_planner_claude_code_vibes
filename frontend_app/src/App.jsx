import { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import AuthPage from './pages/AuthPage'
import RecipeListPage from './pages/RecipeListPage'
import RecipeEditorPage from './pages/RecipeEditorPage'

function App() {
  const { initialize, isLoading, isAuthenticated } = useAuthStore()

  useEffect(() => {
    initialize()
  }, [initialize])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <Router>
      <Routes>
        {/* Auth routes */}
        <Route path="/auth/signin" element={<AuthPage />} />
        <Route path="/auth/signup" element={<AuthPage />} />
        
        {/* Protected routes */}
        <Route
          path="/"
          element={
            isAuthenticated ? <RecipeListPage /> : <Navigate to="/auth/signin" />
          }
        />
        <Route
          path="/recipe/:id"
          element={
            isAuthenticated ? <RecipeEditorPage /> : <Navigate to="/auth/signin" />
          }
        />
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  )
}

export default App