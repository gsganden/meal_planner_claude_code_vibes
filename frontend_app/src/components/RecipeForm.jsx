import { useState } from 'react'

export default function RecipeForm({ recipe, onChange, hasUnsavedChanges }) {
  const [focusedField, setFocusedField] = useState(null)

  const handleAddIngredient = () => {
    const newIngredients = [...(recipe.ingredients || []), { text: '', quantity: '', unit: '' }]
    onChange('ingredients', newIngredients)
  }

  const handleUpdateIngredient = (index, field, value) => {
    const newIngredients = [...recipe.ingredients]
    newIngredients[index] = { ...newIngredients[index], [field]: value }
    onChange('ingredients', newIngredients)
  }

  const handleRemoveIngredient = (index) => {
    const newIngredients = recipe.ingredients.filter((_, i) => i !== index)
    onChange('ingredients', newIngredients)
  }

  const handleAddStep = () => {
    const maxOrder = Math.max(0, ...(recipe.steps || []).map(s => s.order || 0))
    const newSteps = [...(recipe.steps || []), { order: maxOrder + 1, text: '' }]
    onChange('steps', newSteps)
  }

  const handleUpdateStep = (index, value) => {
    const newSteps = [...recipe.steps]
    newSteps[index] = { ...newSteps[index], text: value }
    onChange('steps', newSteps)
  }

  const handleRemoveStep = (index) => {
    const newSteps = recipe.steps.filter((_, i) => i !== index)
    // Reorder remaining steps
    newSteps.forEach((step, i) => {
      step.order = i + 1
    })
    onChange('steps', newSteps)
  }

  const handleReorderStep = (index, direction) => {
    const newSteps = [...recipe.steps]
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    
    if (targetIndex >= 0 && targetIndex < newSteps.length) {
      // Swap steps
      [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]]
      // Update order numbers
      newSteps.forEach((step, i) => {
        step.order = i + 1
      })
      onChange('steps', newSteps)
    }
  }

  return (
    <form className="space-y-6">
      {/* Title */}
      <div>
        <label htmlFor="title" className="block text-sm font-medium text-gray-700">
          Title
        </label>
        <input
          id="title"
          type="text"
          value={recipe.title || ''}
          onChange={(e) => onChange('title', e.target.value)}
          onFocus={() => setFocusedField('title')}
          onBlur={() => setFocusedField(null)}
          placeholder="Untitled Recipe"
          className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            focusedField === 'title' && hasUnsavedChanges ? 'border-yellow-400' : 'border-gray-300'
          }`}
        />
      </div>

      {/* Yield */}
      <div>
        <label htmlFor="yield" className="block text-sm font-medium text-gray-700">
          Yield
        </label>
        <input
          id="yield"
          type="text"
          value={recipe.yield || ''}
          onChange={(e) => onChange('yield', e.target.value)}
          onFocus={() => setFocusedField('yield')}
          onBlur={() => setFocusedField(null)}
          placeholder="e.g., 4 servings"
          className={`mt-1 block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            focusedField === 'yield' && hasUnsavedChanges ? 'border-yellow-400' : 'border-gray-300'
          }`}
        />
      </div>

      {/* Prep Time */}
      <div>
        <label htmlFor="prepTime" className="block text-sm font-medium text-gray-700">
          Prep Time
        </label>
        <input
          id="prepTime"
          type="text"
          value={recipe.prepTime || ''}
          onChange={(e) => onChange('prepTime', e.target.value)}
          placeholder="e.g., 15 minutes"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Cook Time */}
      <div>
        <label htmlFor="cookTime" className="block text-sm font-medium text-gray-700">
          Cook Time
        </label>
        <input
          id="cookTime"
          type="text"
          value={recipe.cookTime || ''}
          onChange={(e) => onChange('cookTime', e.target.value)}
          placeholder="e.g., 30 minutes"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Ingredients */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Ingredients
          </label>
          <button
            type="button"
            onClick={handleAddIngredient}
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            + Add Ingredient
          </button>
        </div>
        
        <div className="space-y-2">
          {(!recipe.ingredients || recipe.ingredients.length === 0) && (
            <p className="text-sm text-gray-500 italic">No ingredients yet. Click "Add Ingredient" to start.</p>
          )}
          
          {recipe.ingredients?.map((ingredient, index) => (
            <div key={index} className="flex items-start space-x-2">
              <input
                type="text"
                value={ingredient.quantity || ''}
                onChange={(e) => handleUpdateIngredient(index, 'quantity', e.target.value)}
                placeholder="Qty"
                className="w-20 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="text"
                value={ingredient.unit || ''}
                onChange={(e) => handleUpdateIngredient(index, 'unit', e.target.value)}
                placeholder="Unit"
                className="w-24 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <input
                type="text"
                value={ingredient.text || ''}
                onChange={(e) => handleUpdateIngredient(index, 'text', e.target.value)}
                placeholder="Ingredient"
                className="flex-1 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                onClick={() => handleRemoveIngredient(index)}
                className="text-red-600 hover:text-red-800"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Steps */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-sm font-medium text-gray-700">
            Instructions
          </label>
          <button
            type="button"
            onClick={handleAddStep}
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            + Add Step
          </button>
        </div>
        
        <div className="space-y-2">
          {(!recipe.steps || recipe.steps.length === 0) && (
            <p className="text-sm text-gray-500 italic">No instructions yet. Click "Add Step" to start.</p>
          )}
          
          {recipe.steps?.map((step, index) => (
            <div key={index} className="flex items-start space-x-2">
              <span className="text-sm text-gray-500 mt-1">{step.order || index + 1}.</span>
              <textarea
                value={step.text || ''}
                onChange={(e) => handleUpdateStep(index, e.target.value)}
                placeholder="Describe this step..."
                rows={2}
                className="flex-1 px-2 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <div className="flex flex-col space-y-1">
                <button
                  type="button"
                  onClick={() => handleReorderStep(index, 'up')}
                  disabled={index === 0}
                  className={`text-gray-400 hover:text-gray-600 ${index === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                <button
                  type="button"
                  onClick={() => handleReorderStep(index, 'down')}
                  disabled={index === recipe.steps.length - 1}
                  className={`text-gray-400 hover:text-gray-600 ${index === recipe.steps.length - 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              <button
                type="button"
                onClick={() => handleRemoveStep(index)}
                className="text-red-600 hover:text-red-800"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
          Notes
        </label>
        <textarea
          id="notes"
          value={recipe.notes || ''}
          onChange={(e) => onChange('notes', e.target.value)}
          placeholder="Additional notes or tips..."
          rows={3}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
    </form>
  )
}