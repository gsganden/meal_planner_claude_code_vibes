import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'
import RecipeForm from '../components/RecipeForm'
import ChatPanel from '../components/ChatPanel'

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
  const wsRef = useRef(null)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [chatMessages, setChatMessages] = useState([])
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

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

  // WebSocket connection
  useEffect(() => {
    if (recipe && id && !wsRef.current) {
      connectWebSocket()
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [id, recipe?.id]) // Connect when we have a recipe ID

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
      const response = await axios.get(`/v1/recipes/${id}`)
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

  const connectWebSocket = () => {
    const token = localStorage.getItem('access_token')
    const wsUrl = `ws://localhost:8000/v1/chat/${id}?token=${token}`
    
    try {
      wsRef.current = new WebSocket(wsUrl)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected to:', wsUrl)
        setWsStatus('connected')
      }
      
      wsRef.current.onmessage = (event) => {
        console.log('WebSocket message received:', event.data)
        const data = JSON.parse(event.data)
        if (data.type === 'recipe_update') {
          const { content, recipe_data, error } = data.payload
          console.log('Recipe update payload:', { content, recipe_data, error })
          
          // Handle errors
          if (error) {
            setChatMessages(prev => [...prev, {
              type: 'error',
              content: error,
              timestamp: new Date().toISOString()
            }])
            return
          }
          
          // Add assistant message to chat if provided
          if (content) {
            setChatMessages(prev => [...prev, {
              type: 'assistant',
              content: content,
              timestamp: new Date().toISOString()
            }])
          }
          
          // Update recipe if data provided
          if (recipe_data) {
            setRecipe(recipe_data)
            setHasUnsavedChanges(false)
            setLastSaveTime(new Date())
          }
        }
      }
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setWsStatus('error')
      }
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        setWsStatus('disconnected')
        wsRef.current = null
        
        // Only attempt to reconnect if it wasn't a normal closure
        if (event.code !== 1000 && recipe) {
          setTimeout(() => {
            if (!wsRef.current) {
              connectWebSocket()
            }
          }, 3000)
        }
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setWsStatus('error')
    }
  }

  const sendChatMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // Add user message to chat
      setChatMessages(prev => [...prev, {
        type: 'user',
        content: message,
        timestamp: new Date().toISOString()
      }])
      
      // Send to server
      const messageData = {
        type: 'chat_message',
        payload: {
          content: message
        }
      }
      console.log('Sending WebSocket message:', messageData)
      wsRef.current.send(JSON.stringify(messageData))
    }
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
      await axios.patch(`/v1/recipes/${id}`, recipeData)
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
      await axios.delete(`/v1/recipes/${id}`)
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
          <ChatPanel
            messages={chatMessages}
            onSendMessage={sendChatMessage}
            connectionStatus={wsStatus}
            recipeName={recipe?.title || 'Untitled Recipe'}
          />
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