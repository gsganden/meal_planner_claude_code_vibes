import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

export default function RecipeListPage() {
  const navigate = useNavigate()
  const { isAuthenticated, logout } = useAuthStore()
  const [recipes, setRecipes] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth/signin')
    }
  }, [isAuthenticated, navigate])

  // Load recipes
  useEffect(() => {
    loadRecipes()
  }, [])

  const loadRecipes = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await axios.get('/v1/recipes')
      setRecipes(response.data)
    } catch (error) {
      setError('Failed to load recipes')
      console.error('Error loading recipes:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateRecipe = async () => {
    try {
      // Create a new recipe with minimal data
      const recipeData = {
        title: '',
        yield: '1 serving',
        ingredients: [{ 
          text: 'Add ingredients here',
          quantity: '1',
          unit: 'item'
        }],
        steps: [{ 
          order: 1,
          text: 'Add instructions here'
        }]
      }
      console.log('Creating recipe with data:', recipeData)
      const response = await axios.post('/v1/recipes', recipeData)
      
      // Navigate to the recipe editor
      navigate(`/recipe/${response.data.id}`)
    } catch (error) {
      console.error('Error creating recipe:', error)
      setError('Failed to create new recipe')
    }
  }

  const handleSignOut = async () => {
    await logout()
    navigate('/auth/signin')
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRecipeDescription = (recipe) => {
    // RecipeSummary only includes yield, not ingredients/steps
    return recipe.yield || 'No yield specified'
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading recipes...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-semibold text-gray-900">
              Recipe Chat Assistant
            </h1>
            <button
              onClick={handleSignOut}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">My Recipes</h2>
          <button
            onClick={handleCreateRecipe}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Recipe
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Recipe list */}
        {recipes.length === 0 ? (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No recipes</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new recipe.
            </p>
            <div className="mt-6">
              <button
                onClick={handleCreateRecipe}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Recipe
              </button>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {recipes.map((recipe) => (
              <div
                key={recipe.id}
                onClick={() => navigate(`/recipe/${recipe.id}`)}
                className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer overflow-hidden"
              >
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {recipe.title || 'Untitled Recipe'}
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    {getRecipeDescription(recipe)}
                  </p>
                  <p className="text-xs text-gray-500">
                    Updated {formatDate(recipe.updated_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}