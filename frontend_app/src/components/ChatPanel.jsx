import { useState, useRef, useEffect } from 'react'

export default function ChatPanel({ messages, onSendMessage, connectionStatus, recipeName }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && connectionStatus === 'connected') {
      onSendMessage(input)
      setInput('')
    }
  }

  const handleQuickAction = (action) => {
    onSendMessage(action)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Connection status */}
      <div className="border-b border-gray-200 px-4 py-2 text-sm">
        {connectionStatus === 'connected' && <span className="text-green-600">Connected</span>}
        {connectionStatus === 'disconnected' && <span className="text-yellow-600">Disconnected</span>}
        {connectionStatus === 'error' && <span className="text-red-600">Connection lost</span>}
      </div>

      {/* Chat header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-900">Chat</h2>
        <p className="text-sm text-gray-500">Chat to edit "{recipeName}"</p>
      </div>

      {/* Quick actions */}
      <div className="px-4 py-3 border-b border-gray-200 space-y-2">
        <p className="text-xs text-gray-500 uppercase tracking-wide">Quick Actions</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleQuickAction('Scale this recipe to serve 8 people')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Scale Recipe
          </button>
          <button
            onClick={() => handleQuickAction('Simplify the instructions')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Simplify
          </button>
          <button
            onClick={() => handleQuickAction('Make this recipe healthier')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Make Healthier
          </button>
          <button
            onClick={() => handleQuickAction('Add cooking tips and tricks')}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Add Tips
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-sm">How can I help you with this recipe?</p>
            <p className="text-xs mt-2">Try pasting a recipe, asking for modifications, or requesting suggestions.</p>
          </div>
        )}
        
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.type === 'user'
                  ? 'bg-blue-600 text-white'
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
        <div ref={messagesEndRef} />
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} className="px-4 py-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste a recipe or type a message..."
            disabled={connectionStatus !== 'connected'}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || connectionStatus !== 'connected'}
            className={`px-4 py-2 rounded-md font-medium ${
              input.trim() && connectionStatus === 'connected'
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Paste recipes, ask for changes, or request cooking tips
        </p>
      </form>
    </div>
  )
}