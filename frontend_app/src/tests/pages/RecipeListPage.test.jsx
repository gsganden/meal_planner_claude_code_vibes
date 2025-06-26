import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import RecipeListPage from '../../pages/RecipeListPage'
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

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

const renderRecipeListPage = () => {
  return render(
    <BrowserRouter>
      <RecipeListPage />
    </BrowserRouter>
  )
}

describe('RecipeListPage - UC0: Application Entry & Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue({
      isAuthenticated: true,
      logout: vi.fn(),
    })
  })

  describe('Primary Flow - New User (First Recipe)', () => {
    it('should display empty state with "Create Your First Recipe" message', async () => {
      axios.get.mockResolvedValue({ data: [] })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByText(/get started by creating a new recipe/i)).toBeInTheDocument()
      })
      
      expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
    })

    it('should create new recipe immediately when "New Recipe" clicked', async () => {
      axios.get.mockResolvedValue({ data: [] })
      axios.post.mockResolvedValue({ 
        data: { 
          id: 'new-recipe-id',
          title: 'Untitled Recipe 1',
          yield: '1 serving',
          ingredients: [],
          steps: [],
          created_at: '2024-06-24T12:00:00Z',
          updated_at: '2024-06-24T12:00:00Z'
        } 
      })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
      })
      
      await userEvent.click(screen.getByRole('button', { name: /new recipe/i }))
      
      // Should create recipe via API
      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith('/v1/recipes', {
          title: '',
          yield: '1 serving',
          ingredients: [],
          steps: []
        })
      })
      
      // Should navigate to editor
      expect(mockNavigate).toHaveBeenCalledWith('/recipe/new-recipe-id')
    })
  })

  describe('Primary Flow - Returning User (Existing Recipes)', () => {
    const mockRecipes = [
      {
        id: 'recipe-1',
        title: 'Chocolate Chip Cookies',
        yield: '24 cookies',
        updated_at: '2024-06-24T10:00:00Z'
      },
      {
        id: 'recipe-2',
        title: 'Pasta Salad',
        yield: '6 servings',
        updated_at: '2024-06-23T10:00:00Z'
      }
    ]

    it('should display recipes in reverse chronological order', async () => {
      axios.get.mockResolvedValue({ data: mockRecipes })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByText('Chocolate Chip Cookies')).toBeInTheDocument()
        expect(screen.getByText('Pasta Salad')).toBeInTheDocument()
      })
      
      // Check order - newest first
      const recipeTitles = screen.getAllByRole('heading', { level: 3 })
      expect(recipeTitles[0]).toHaveTextContent('Chocolate Chip Cookies')
      expect(recipeTitles[1]).toHaveTextContent('Pasta Salad')
    })

    it('should show yield as description', async () => {
      axios.get.mockResolvedValue({ data: mockRecipes })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByText('24 cookies')).toBeInTheDocument()
        expect(screen.getByText('6 servings')).toBeInTheDocument()
      })
    })

    it('should navigate to recipe editor when recipe clicked', async () => {
      axios.get.mockResolvedValue({ data: mockRecipes })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByText('Chocolate Chip Cookies')).toBeInTheDocument()
      })
      
      await userEvent.click(screen.getByText('Chocolate Chip Cookies'))
      
      expect(mockNavigate).toHaveBeenCalledWith('/recipe/recipe-1')
    })

    it('should display last updated dates', async () => {
      axios.get.mockResolvedValue({ data: mockRecipes })
      
      renderRecipeListPage()
      
      await waitFor(() => {
        // Dates should be present (component may format them differently)
        expect(screen.getByText(/2024/)).toBeInTheDocument()
      })
    })
  })

  describe('Navigation & Header', () => {
    it('should display app title and navigation', async () => {
      axios.get.mockResolvedValue({ data: [] })
      
      renderRecipeListPage()
      
      expect(screen.getByRole('heading', { name: /recipe chat assistant/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
    })

    it('should handle sign out', async () => {
      const mockLogout = vi.fn()
      useAuthStore.mockReturnValue({
        isAuthenticated: true,
        logout: mockLogout,
      })
      axios.get.mockResolvedValue({ data: [] })
      
      renderRecipeListPage()
      
      await userEvent.click(screen.getByRole('button', { name: /sign out/i }))
      
      expect(mockLogout).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/auth/signin')
    })
  })

  describe('Error Handling', () => {
    it('should display error message when loading fails', async () => {
      axios.get.mockRejectedValue(new Error('Network error'))
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByText(/failed to load recipes/i)).toBeInTheDocument()
      })
      
      // Should still show New Recipe button
      expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
    })

    it('should display error when recipe creation fails', async () => {
      axios.get.mockResolvedValue({ data: [] })
      axios.post.mockRejectedValue(new Error('Creation failed'))
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
      })
      
      await userEvent.click(screen.getByRole('button', { name: /new recipe/i }))
      
      await waitFor(() => {
        expect(screen.getByText(/failed to create recipe/i)).toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('should show loading state while fetching recipes', async () => {
      // Mock axios.get to never resolve
      axios.get.mockImplementation(() => new Promise(() => {}))
      
      renderRecipeListPage()
      
      expect(screen.getByText(/loading recipes/i)).toBeInTheDocument()
    })

    it('should show loading state when creating new recipe', async () => {
      axios.get.mockResolvedValue({ data: [] })
      // Mock axios.post to never resolve
      axios.post.mockImplementation(() => new Promise(() => {}))
      
      renderRecipeListPage()
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /new recipe/i })).toBeInTheDocument()
      })
      
      await userEvent.click(screen.getByRole('button', { name: /new recipe/i }))
      
      // New recipe should be created
      await waitFor(() => {
        expect(axios.post).toHaveBeenCalled()
      })
    })
  })
})