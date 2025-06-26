import React from 'react';
import { ConnectionState } from '@/lib/websocket';

interface ConnectionStatusProps {
  state: ConnectionState;
  className?: string;
}

export function ConnectionStatus({ state, className = '' }: ConnectionStatusProps) {
  const statusConfig: Record<ConnectionState, { color: string; text: string; pulseColor?: string }> = {
    disconnected: { 
      color: 'bg-red-500', 
      text: 'Disconnected' 
    },
    connecting: { 
      color: 'bg-yellow-500', 
      text: 'Connecting...', 
      pulseColor: 'bg-yellow-400' 
    },
    authenticating: { 
      color: 'bg-yellow-500', 
      text: 'Authenticating...', 
      pulseColor: 'bg-yellow-400' 
    },
    authenticated: { 
      color: 'bg-green-500', 
      text: 'Connected' 
    },
    reconnecting: { 
      color: 'bg-orange-500', 
      text: 'Reconnecting...', 
      pulseColor: 'bg-orange-400' 
    },
    error: { 
      color: 'bg-red-500', 
      text: 'Connection Error' 
    }
  };

  const config = statusConfig[state];

  return (
    <div className={`flex items-center gap-2 text-sm ${className}`}>
      <div className="relative">
        <span 
          className={`block w-2 h-2 rounded-full ${config.color}`}
          aria-hidden="true"
        />
        {config.pulseColor && (
          <span 
            className={`absolute inset-0 w-2 h-2 rounded-full animate-ping ${config.pulseColor} opacity-75`}
            aria-hidden="true"
          />
        )}
      </div>
      <span className="text-gray-600 dark:text-gray-400">
        {config.text}
      </span>
    </div>
  );
}