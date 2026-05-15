import React from 'react'
import { useAppStore } from '@/store/store'
import { useHealth } from '@/hooks/useHealth'
import { ChatInterface } from '@/components/ChatInterface'
import { QueryBuilder } from '@/components/QueryBuilder'
import { Menu, X, Moon, Sun, AlertCircle } from 'lucide-react'

export const App: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    darkMode,
    toggleDarkMode,
    sidebarOpen,
    toggleSidebar,
    selectedProvider,
    setProvider,
    selectedModel,
    setModel,
  } = useAppStore()

  const { data: health } = useHealth()

  const tabClasses = (tab: string) =>
    `px-4 py-2 font-medium transition ${
      activeTab === tab
        ? 'border-b-2 border-nycblue-500 text-nycblue-600'
        : 'text-gray-600 hover:text-gray-900 border-b-2 border-transparent'
    }`

  return (
    <div className={`flex h-screen overflow-hidden ${darkMode ? 'dark bg-gray-900' : 'bg-gray-50'}`}>
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } transition-all duration-300 bg-nycblue-900 text-white overflow-hidden flex flex-col`}
      >
        {/* Logo */}
        <div className="px-6 py-4 border-b border-nycblue-700/50">
          <h1 className="text-xl font-bold">NYC Data</h1>
          <p className="text-xs text-nycblue-200">Assistant Suite</p>
        </div>

        {/* Settings */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-nycblue-200 mb-2">
              LLM Provider
            </label>
            <select
              value={selectedProvider}
              onChange={(e) => setProvider(e.target.value as 'ollama' | 'openai' | 'huggingface')}
              className="w-full px-3 py-2 rounded bg-nycblue-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-nycblue-500"
              aria-label="Select LLM provider"
            >
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI (API)</option>
              <option value="huggingface">Hugging Face (API)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-nycblue-200 mb-2">Model</label>
            <input
              type="text"
              value={selectedModel}
              onChange={(e) => setModel(e.target.value)}
              placeholder="e.g., mistral"
              className="w-full px-3 py-2 rounded bg-nycblue-800 text-white text-sm focus:outline-none focus:ring-2 focus:ring-nycblue-500"
              aria-label="Model name"
            />
          </div>

          {/* Health Status */}
          {health && (
            <div className="mt-6 p-3 bg-nycblue-800 rounded">
              <p className="text-xs font-semibold text-nycblue-200 mb-2">System Status</p>
              <div className="space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      health.database ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span>Database</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      health.chatbot ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span>Chatbot</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      health.query_engine ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span>Query Engine</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-nycblue-700/50 text-xs text-nycblue-300">
          <p>NYC Sidewalk Data Toolkit</p>
          <p>v1.1.0</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div
          className={`${
            darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
          } border-b shadow-sm flex-shrink-0`}
        >
          <div className="flex items-center justify-between px-6 py-4">
            {/* Left: Menu + Title */}
            <div className="flex items-center gap-4">
              <button
                onClick={toggleSidebar}
                className={`p-2 rounded-lg transition ${
                  darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
                }`}
                aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
              >
                {sidebarOpen ? (
                  <X className="w-5 h-5" />
                ) : (
                  <Menu className="w-5 h-5" />
                )}
              </button>
              <h1
                className={`text-xl font-bold ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}
              >
                NYC Data Assistant
              </h1>
            </div>

            {/* Right: Theme Toggle */}
            <button
              onClick={toggleDarkMode}
              className={`p-2 rounded-lg transition ${
                darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
              }`}
              aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {darkMode ? (
                <Sun className="w-5 h-5 text-yellow-400" />
              ) : (
                <Moon className="w-5 h-5 text-gray-600" />
              )}
            </button>
          </div>

          {/* Tabs */}
          <div className={`flex px-6 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
            <button
              onClick={() => setActiveTab('chat')}
              className={`${tabClasses('chat')} ${darkMode ? 'text-gray-300' : ''}`}
            >
              💬 Chat
            </button>
            <button
              onClick={() => setActiveTab('query')}
              className={`${tabClasses('query')} ${darkMode ? 'text-gray-300' : ''}`}
            >
              📊 Query Builder
            </button>
            <button
              onClick={() => setActiveTab('quality')}
              className={`${tabClasses('quality')} ${darkMode ? 'text-gray-300' : ''}`}
            >
              ✓ Quality Check
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'chat' && <ChatInterface />}
          {activeTab === 'query' && <QueryBuilder />}
          {activeTab === 'quality' && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <AlertCircle className="w-12 h-12 mb-3 opacity-50 mx-auto" />
                <p>Data Quality Check coming soon</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
