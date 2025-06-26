import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { ConnectionStatus } from '../components/ConnectionStatus';

export default function WebSocketDemo() {
  const [recipeId, setRecipeId] = useState('');
  const [connectedRecipeId, setConnectedRecipeId] = useState('');
  const { state, messages, sendMessage, error, reconnect } = useWebSocket(connectedRecipeId);

  const handleConnect = () => {
    if (recipeId.trim()) {
      setConnectedRecipeId(recipeId.trim());
    }
  };

  const handleDisconnect = () => {
    setConnectedRecipeId('');
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">WebSocket Demo</h1>
        
        {/* Connection Controls */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Connection</h2>
          
          <div className="flex items-center gap-4 mb-4">
            <input
              type="text"
              placeholder="Recipe ID"
              value={recipeId}
              onChange={(e) => setRecipeId(e.target.value)}
              disabled={connectedRecipeId !== ''}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            
            {connectedRecipeId === '' ? (
              <button
                onClick={handleConnect}
                disabled={!recipeId.trim()}
                className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Connect
              </button>
            ) : (
              <button
                onClick={handleDisconnect}
                className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Disconnect
              </button>
            )}
          </div>
          
          <ConnectionStatus state={state} />
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 text-red-800 rounded-lg flex items-center justify-between">
              <span>{error}</span>
              {state === 'error' && (
                <button
                  onClick={reconnect}
                  className="text-sm underline hover:no-underline"
                >
                  Retry
                </button>
              )}
            </div>
          )}
        </div>

        {/* Connection States */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Connection States</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <h3 className="font-medium text-gray-700">Current State</h3>
              <p className="text-2xl font-mono mt-1">{state}</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-700">Recipe ID</h3>
              <p className="text-2xl font-mono mt-1">{connectedRecipeId || 'None'}</p>
            </div>
            <div>
              <h3 className="font-medium text-gray-700">Messages</h3>
              <p className="text-2xl font-mono mt-1">{messages.length}</p>
            </div>
          </div>
        </div>

        {/* Message Log */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Message Log</h2>
          <div className="h-96 overflow-y-auto border border-gray-200 rounded-lg p-4 font-mono text-sm">
            {messages.length === 0 ? (
              <p className="text-gray-500">No messages yet...</p>
            ) : (
              messages.map((msg, index) => (
                <div key={index} className="mb-4 pb-4 border-b border-gray-100 last:border-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className={`px-2 py-1 rounded text-xs ${
                      msg.type === 'chat_message' ? 'bg-blue-100 text-blue-800' :
                      msg.type === 'recipe_update' ? 'bg-green-100 text-green-800' :
                      msg.type === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {msg.type}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(msg.payload, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Test Actions */}
        {state === 'authenticated' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Test Actions</h2>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => sendMessage('Give me tips for this recipe')}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
              >
                Get Recipe Tips
              </button>
              <button
                onClick={() => sendMessage('Make it vegetarian')}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
              >
                Make Vegetarian
              </button>
              <button
                onClick={() => sendMessage('Scale to 8 servings')}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
              >
                Scale Recipe
              </button>
              <button
                onClick={() => sendMessage('Create a chocolate cake recipe')}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
              >
                Create New Recipe
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}