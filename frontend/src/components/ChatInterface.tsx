import React, { useEffect, useRef, useState } from 'react'
import { useAppStore } from '@/store/store'
import { apiClient } from '@/api/client'
import { Send, Loader, AlertCircle, Trash2 } from 'lucide-react'

export const ChatInterface: React.FC = () => {
  const {
    messages,
    isLoading,
    error,
    addMessage,
    setLoading,
    setError,
    clearMessages,
    selectedProvider,
    selectedModel,
  } = useAppStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    // Add user message
    const userMessage = {
      id: `msg_${Date.now()}_user`,
      role: 'user' as const,
      content: input,
      timestamp: new Date().toISOString(),
    }

    addMessage(userMessage)
    setInput('')
    setError(null)
    setLoading(true)

    try {
      const response = await apiClient.sendChatMessage({
        message: input,
        provider: selectedProvider,
        model: selectedModel,
      })

      const assistantMessage = {
        id: response.message_id,
        role: 'assistant' as const,
        content: response.response,
        timestamp: response.timestamp,
      }

      addMessage(assistantMessage)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
      setError(errorMessage)

      const errorMsg = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant' as const,
        content: `Error: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      }
      addMessage(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSendMessage(e as any)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">NYC Data Assistant</h2>
            <p className="text-sm text-gray-600">
              Powered by {selectedProvider} ({selectedModel})
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={() => clearMessages()}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
              title="Clear conversation"
            >
              <Trash2 className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <h3 className="text-lg font-medium mb-2">Welcome to NYC Data Assistant</h3>
              <p className="text-sm mb-4">
                Ask questions about NYC sidewalk data or use natural language queries to explore the database.
              </p>
              <div className="text-xs space-y-2">
                <p>💬 Example: "What are the most common sidewalk defects?"</p>
                <p>📊 Example: "Show me potholes in Manhattan"</p>
                <p>📈 Example: "Compare maintenance costs by borough"</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-nycblue-500 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-900 rounded-bl-none'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className="text-xs opacity-70 mt-1">
                {new Date(message.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg rounded-bl-none">
              <Loader className="w-5 h-5 animate-spin" />
            </div>
          </div>
        )}

        {error && (
          <div className="flex justify-start">
            <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg rounded-bl-none max-w-xs">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-6 py-4 border-t border-gray-200">
        <form onSubmit={handleSendMessage} className="space-y-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question or describe what you want to analyze... (Ctrl+Enter to send)"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nycblue-500 resize-none"
            rows={3}
            disabled={isLoading}
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setInput('')}
              className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition"
              disabled={isLoading}
            >
              Clear
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-nycblue-500 text-white hover:bg-nycblue-600 rounded-lg transition flex items-center gap-2 disabled:opacity-50"
              disabled={isLoading || !input.trim()}
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
