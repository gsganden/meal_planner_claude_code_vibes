import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import { useWebSocket } from '../hooks/useWebSocket.js'
import RecipeForm from '../components/RecipeForm'
import { ConnectionStatus } from '../components/ConnectionStatus'

export default function RecipeEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()
  const [recipe, setRecipe] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [lastSaveTime, setLastSaveTime] = useState(null)
  const saveTimeoutRef = useRef(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  
  // Use the new WebSocket hook
  const { state: wsState, messages, sendMessage, lastRecipeUpdate, error: wsError } = useWebSocket(id)

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth/signin')
    }
  }, [isAuthenticated, navigate])

  // Load recipe
  useEffect(() => {
    if (id) {
      loadRecipe()
    }
  }, [id])

  // Handle recipe updates from WebSocket
  useEffect(() => {
    if (lastRecipeUpdate?.payload.recipe_data) {
      setRecipe(lastRecipeUpdate.payload.recipe_data)
      setHasUnsavedChanges(false)
      setLastSaveTime(new Date())
    }
  }, [lastRecipeUpdate])

  // Warn about unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  const loadRecipe = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await axios.get(`/recipes/${id}`)
      setRecipe(response.data)
    } catch (error) {
      console.error('Error loading recipe:', error)
      setError('Failed to load recipe')
      if (error.response?.status === 404) {
        navigate('/')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // Convert WebSocket messages to chat format
  const getChatMessages = () => {
    return messages.map(msg => {
      if (msg.type === 'chat_message') {
        return {
          type: 'user',
          content: msg.payload.content,
          timestamp: msg.timestamp
        }
      } else if (msg.type === 'recipe_update') {
        return {
          type: 'assistant',
          content: msg.payload.content,
          timestamp: msg.timestamp
        }
      } else if (msg.type === 'error') {
        return {
          type: 'error',
          content: msg.payload.message,
          timestamp: msg.timestamp
        }
      }
      return null
    }).filter(Boolean)
  }

  const handleRecipeChange = useCallback((field, value) => {
    setRecipe(prev => ({
      ...prev,
      [field]: value
    }))
    setHasUnsavedChanges(true)
    
    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    
    // Set new timeout for autosave (2 seconds)
    saveTimeoutRef.current = setTimeout(() => {
      saveRecipe({ ...recipe, [field]: value })
    }, 2000)
  }, [recipe])

  const saveRecipe = async (recipeData = recipe) => {
    try {
      setIsSaving(true)
      await axios.patch(`/recipes/${id}`, recipeData)
      setHasUnsavedChanges(false)
      setLastSaveTime(new Date())
    } catch (error) {
      console.error('Error saving recipe:', error)
      setError('Failed to save recipe')
    } finally {
      setIsSaving(false)
    }
  }

  const handleExplicitSave = () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveRecipe()
  }

  const handleBack = () => {
    if (hasUnsavedChanges) {
      const confirm = window.confirm('You have unsaved changes. Are you sure you want to leave?')
      if (!confirm) return
    }
    navigate('/')
  }

  const handleDelete = () => {
    setShowDeleteConfirm(true)
  }

  const confirmDelete = async () => {
    try {
      await axios.delete(`/recipes/${id}`)
      navigate('/')
    } catch (error) {
      console.error('Error deleting recipe:', error)
      setError('Failed to delete recipe')
    }
    setShowDeleteConfirm(false)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading recipe...</div>
      </div>
    )
  }

  if (error && !recipe) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600">{error}</div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm flex-shrink-0">
        <div className="px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="text-gray-600 hover:text-gray-900"
              aria-label="Back"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-900">
              {recipe?.title || 'Untitled Recipe'}
            </h1>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Save status */}
            <div className="text-sm">
              {isSaving && <span className="text-gray-500">Saving...</span>}
              {!isSaving && hasUnsavedChanges && <span className="text-gray-500">Unsaved changes</span>}
              {!isSaving && !hasUnsavedChanges && !error && <span className="text-gray-500">Saved</span>}
              {error && <span className="text-red-600">{error}</span>}
            </div>
            
            {/* Save button */}
            <button
              onClick={handleExplicitSave}
              disabled={!hasUnsavedChanges || isSaving}
              className={`px-4 py-2 rounded-md text-sm font-medium ${
                hasUnsavedChanges && !isSaving
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              aria-label="Save"
            >
              Save
            </button>
            
            {/* Delete button */}
            <button
              onClick={handleDelete}
              className="text-red-600 hover:text-red-800 text-sm font-medium"
              aria-label="Delete"
            >
              Delete
            </button>
          </div>
        </div>
      </header>

      {/* Main content - two panes */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left pane - Chat (40%) */}
        <div className="w-2/5 border-r border-gray-200 flex flex-col bg-white">
          <div className="flex flex-col h-full">
            {/* Connection status */}
            <div className="border-b border-gray-200 px-4 py-2 text-sm flex items-center justify-between">
              <span>Recipe Assistant</span>
              <ConnectionStatus state={wsState} />
            </div>

            {/* Chat header */}
            <div className="px-4 py-3 border-b border-gray-200">
              <h2 className="text-lg font-medium text-gray-900">Chat</h2>
              <p className="text-sm text-gray-500">Chat to edit "{recipe?.title || 'Untitled Recipe'}"</p>
            </div>

            {/* Chat messages using RecipeChat component style */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {wsError && (
                <div className="text-center text-red-500">
                  {wsError}
                </div>
              )}
              
              {getChatMessages().length === 0 && (
                <div className="text-center text-gray-500 mt-8">
                  <p className="text-sm">How can I help you with this recipe?</p>
                  <p className="text-xs mt-2">Try pasting a recipe, asking for modifications, or requesting suggestions.</p>
                </div>
              )}
              
              {getChatMessages().map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                      message.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : message.type === 'error'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p className={`text-xs mt-1 ${
                      message.type === 'user' ? 'text-blue-200' : 'text-gray-500'
                    }`}>
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Input form */}
            <form onSubmit={(e) => {
              e.preventDefault()
              const input = e.target.message.value.trim()
              if (input && wsState === 'authenticated') {
                sendMessage(input)
                e.target.message.value = ''
              }
            }} className="px-4 py-4 border-t border-gray-200">
              <div className="flex space-x-2">
                <input
                  name="message"
                  type="text"
                  placeholder={
                    wsState === 'authenticated'
                      ? 'Paste a recipe or type a message...'
                      : wsState === 'connecting' || wsState === 'authenticating'
                      ? 'Connecting...'
                      : 'Not connected'
                  }
                  disabled={wsState !== 'authenticated'}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
                <button
                  type="submit"
                  disabled={wsState !== 'authenticated'}
                  className={`px-4 py-2 rounded-md font-medium ${
                    wsState === 'authenticated'
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  Send
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right pane - Recipe form (60%) */}
        <div className="flex-1 overflow-y-auto bg-white">
          <div className="max-w-3xl mx-auto p-6">
            <RecipeForm
              recipe={recipe}
              onChange={handleRecipeChange}
              hasUnsavedChanges={hasUnsavedChanges}
            />
          </div>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Are you sure you want to delete this recipe?
            </h3>
            <div className="flex space-x-3">
              <button
                onClick={confirmDelete}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
                aria-label="Confirm"
              >
                Yes, Delete
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}