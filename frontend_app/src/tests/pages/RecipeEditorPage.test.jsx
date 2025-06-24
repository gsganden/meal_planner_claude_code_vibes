import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import RecipeEditorPage from '../../pages/RecipeEditorPage'
import { useAuthStore } from '../../stores/authStore'
import axios from 'axios'

// Mock dependencies
vi.mock('../../stores/authStore')

// Mock axios
vi.mock('axios', () => ({
  default: {
    defaults: { baseURL: '' },
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    create: vi.fn(() => ({
      defaults: { baseURL: '' },
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
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

// Mock WebSocket
global.WebSocket = vi.fn()
global.WebSocket.OPEN = 1
global.WebSocket.CLOSED = 3

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: 'test-recipe-id' }),
  }
})

const renderRecipeEditorPage = () => {
  return render(<RecipeEditorPage />)
}

// Mock recipe data
const mockRecipe = {
  id: 'test-recipe-id',
  title: 'Test Recipe',
  yield: '4 servings',
  description: 'A test recipe',
  prep_time_minutes: 15,
  cook_time_minutes: 30,
  ingredients: [
    { text: '2 cups flour', optional: false },
    { text: '1 cup sugar', optional: false }
  ],
  steps: [
    { text: 'Mix ingredients', optional: false },
    { text: 'Bake at 350°F', optional: false }
  ],
  tags: ['dessert'],
  created_at: '2024-06-24T12:00:00Z',
  updated_at: '2024-06-24T12:00:00Z'
}

describe('RecipeEditorPage - UC1, UC2, UC3: Recipe Editing', () => {
  let mockWebSocket

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue({
      isAuthenticated: true,
    })

    // Mock WebSocket
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: 1, // WebSocket.OPEN
    }
    global.WebSocket.mockImplementation(() => {
      // Simulate connection opening after a short delay
      setTimeout(() => {
        const openHandler = mockWebSocket.addEventListener.mock.calls.find(
          call => call[0] === 'open'
        )?.[1]
        if (openHandler) {
          openHandler()
        }
      }, 0)
      return mockWebSocket
    })

    // Default axios mock
    axios.get.mockResolvedValue({ data: mockRecipe })
    axios.patch.mockResolvedValue({ data: mockRecipe })
  })

  describe('UC1: Extract Recipe from Text', () => {
    it('should allow pasting recipe text into chat', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      }, { timeout: 3000 })

      // Wait for WebSocket to be connected
      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument()
      }, { timeout: 2000 })

      const chatInput = screen.getByPlaceholderText(/paste a recipe|type a message/i)
      const recipeText = `Classic Chocolate Chip Cookies
      
      Ingredients:
      - 2 cups all-purpose flour
      - 1 tsp baking soda
      - 1 cup butter
      - 1 cup sugar
      
      Instructions:
      1. Preheat oven to 350°F
      2. Mix dry ingredients
      3. Cream butter and sugar
      4. Combine and bake for 12 minutes`

      await userEvent.type(chatInput, recipeText)
      await userEvent.keyboard('{Enter}')

      // Should send message via WebSocket
      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'chat_message',
          payload: { content: recipeText }
        })
      )
    })

    it('should update recipe form when extraction response received', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Simulate WebSocket message from server
      const extractedRecipe = {
        type: 'recipe_update',
        payload: {
          recipe: {
            ...mockRecipe,
            title: 'Classic Chocolate Chip Cookies',
            ingredients: [
              { text: '2 cups all-purpose flour', optional: false },
              { text: '1 tsp baking soda', optional: false },
              { text: '1 cup butter', optional: false },
              { text: '1 cup sugar', optional: false }
            ],
            steps: [
              { text: 'Preheat oven to 350°F', optional: false },
              { text: 'Mix dry ingredients', optional: false },
              { text: 'Cream butter and sugar', optional: false },
              { text: 'Combine and bake for 12 minutes', optional: false }
            ]
          },
          message: 'I found a recipe for Classic Chocolate Chip Cookies! I\'ve updated the recipe for you.'
        }
      }

      // Trigger WebSocket message event
      const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )[1]
      
      act(() => {
        messageHandler({ data: JSON.stringify(extractedRecipe) })
      })

      // Check that form is updated
      await waitFor(() => {
        expect(screen.getByDisplayValue('Classic Chocolate Chip Cookies')).toBeInTheDocument()
      })
    })
  })

  describe('UC2: Refine Recipe via Chat', () => {
    it('should allow requesting recipe modifications', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      const chatInput = screen.getByPlaceholderText(/paste a recipe|type a message/i)
      await userEvent.type(chatInput, 'make this recipe vegan')
      await userEvent.keyboard('{Enter}')

      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'chat_message',
          payload: { content: 'make this recipe vegan' }
        })
      )
    })

    it('should show quick action buttons', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Check for quick action buttons
      expect(screen.getByText(/scale recipe/i)).toBeInTheDocument()
      expect(screen.getByText(/simplify/i)).toBeInTheDocument()
      expect(screen.getByText(/make healthier/i)).toBeInTheDocument()
      expect(screen.getByText(/add tips/i)).toBeInTheDocument()
    })

    it('should send quick action when button clicked', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByText(/scale recipe/i))

      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'chat_message',
          payload: { content: 'Scale this recipe to serve 8 people' }
        })
      )
    })
  })

  describe('UC3: Generate Recipe from Description', () => {
    it('should allow generating new recipe from description', async () => {
      // Mock empty recipe for new recipe creation
      axios.get.mockResolvedValue({ 
        data: {
          id: 'test-recipe-id',
          title: '',
          yield: '1 serving',
          ingredients: [],
          steps: [],
          created_at: '2024-06-24T12:00:00Z',
          updated_at: '2024-06-24T12:00:00Z'
        }
      })

      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText(/untitled recipe/i)).toBeInTheDocument()
      })

      const chatInput = screen.getByPlaceholderText(/paste a recipe|type a message/i)
      await userEvent.type(chatInput, 'I need a quick healthy lunch recipe with chicken')
      await userEvent.keyboard('{Enter}')

      expect(mockWebSocket.send).toHaveBeenCalledWith(
        JSON.stringify({
          type: 'chat_message',
          payload: { content: 'I need a quick healthy lunch recipe with chicken' }
        })
      )
    })
  })

  describe('UC4: Direct Field Editing with Chat Sync', () => {
    it('should allow direct editing of recipe fields', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Recipe')).toBeInTheDocument()
      })

      const titleInput = screen.getByLabelText(/title/i)
      await userEvent.clear(titleInput)
      await userEvent.type(titleInput, 'Updated Recipe Title')

      // Should show unsaved indicator
      expect(titleInput).toHaveClass(/border-yellow-500|unsaved/i)
    })

    it('should autosave after 2 seconds of inactivity', async () => {
      vi.useFakeTimers()
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Recipe')).toBeInTheDocument()
      })

      const titleInput = screen.getByLabelText(/title/i)
      await userEvent.clear(titleInput)
      await userEvent.type(titleInput, 'Updated Recipe Title')

      // Fast forward 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000)
      })

      await waitFor(() => {
        expect(axios.patch).toHaveBeenCalledWith(
          '/v1/recipes/test-recipe-id',
          expect.objectContaining({
            title: 'Updated Recipe Title'
          })
        )
      })

      vi.useRealTimers()
    })

    it('should show save status indicators', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Recipe')).toBeInTheDocument()
      })

      // Should show "Saved" initially
      expect(screen.getByText(/saved/i)).toBeInTheDocument()

      const titleInput = screen.getByLabelText(/title/i)
      await userEvent.type(titleInput, ' Updated')

      // Should show "Unsaved changes"
      expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument()
    })
  })

  describe('Layout and Navigation', () => {
    it('should display two-pane layout with chat and recipe form', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Check for main layout elements
      expect(screen.getByRole('heading', { name: /chat/i })).toBeInTheDocument()
      expect(screen.getByRole('form')).toBeInTheDocument()
      expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/yield/i)).toBeInTheDocument()
    })

    it('should handle back navigation', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByRole('button', { name: /back/i }))

      expect(mockNavigate).toHaveBeenCalledWith('/')
    })

    it('should handle delete recipe', async () => {
      axios.delete.mockResolvedValue({})
      
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      await userEvent.click(screen.getByRole('button', { name: /delete/i }))

      // Should show confirmation dialog
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument()

      await userEvent.click(screen.getByRole('button', { name: /confirm|yes/i }))

      await waitFor(() => {
        expect(axios.delete).toHaveBeenCalledWith('/v1/recipes/test-recipe-id')
        expect(mockNavigate).toHaveBeenCalledWith('/')
      })
    })
  })

  describe('WebSocket Connection Management', () => {
    it('should show connection status', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText(/connected/i)).toBeInTheDocument()
      })
    })

    it('should handle disconnection', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Simulate disconnect
      mockWebSocket.readyState = WebSocket.CLOSED
      const closeHandler = mockWebSocket.addEventListener.mock.calls.find(
        call => call[0] === 'close'
      )[1]
      
      act(() => {
        closeHandler()
      })

      expect(screen.getByText(/disconnected|connection lost/i)).toBeInTheDocument()
    })

    it('should disable chat when disconnected', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Simulate disconnect
      mockWebSocket.readyState = WebSocket.CLOSED
      const closeHandler = mockWebSocket.addEventListener.mock.calls.find(
        call => call[0] === 'close'
      )[1]
      
      act(() => {
        closeHandler()
      })

      const chatInput = screen.getByPlaceholderText(/paste a recipe|type a message/i)
      expect(chatInput).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('should display error when recipe fails to load', async () => {
      axios.get.mockRejectedValue(new Error('Failed to load'))
      
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText(/failed to load recipe/i)).toBeInTheDocument()
      })
    })

    it('should display error when save fails', async () => {
      axios.patch.mockRejectedValue(new Error('Save failed'))
      
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByDisplayValue('Test Recipe')).toBeInTheDocument()
      })

      const titleInput = screen.getByLabelText(/title/i)
      await userEvent.type(titleInput, ' Updated')

      // Trigger save
      await userEvent.click(screen.getByRole('button', { name: /save/i }))

      await waitFor(() => {
        expect(screen.getByText(/failed to save/i)).toBeInTheDocument()
      })
    })

    it('should handle WebSocket errors gracefully', async () => {
      renderRecipeEditorPage()

      await waitFor(() => {
        expect(screen.getByText('Test Recipe')).toBeInTheDocument()
      })

      // Simulate error message
      const errorHandler = mockWebSocket.addEventListener.mock.calls.find(
        call => call[0] === 'message'
      )[1]
      
      act(() => {
        errorHandler({
          data: JSON.stringify({
            type: 'recipe_update',
            payload: {
              error: 'Unable to process your request'
            }
          })
        })
      })

      expect(screen.getByText(/unable to process your request/i)).toBeInTheDocument()
    })
  })
})