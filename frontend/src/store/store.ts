import { create } from 'zustand'
import { ChatResponse } from '@/api/client'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface AppState {
  // Chat state
  messages: Message[]
  isLoading: boolean
  error: string | null
  
  // UI state
  activeTab: 'chat' | 'query' | 'quality'
  darkMode: boolean
  sidebarOpen: boolean
  
  // Settings
  selectedProvider: 'ollama' | 'openai' | 'huggingface'
  selectedModel: string
  
  // Actions
  addMessage: (message: Message) => void
  clearMessages: () => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setActiveTab: (tab: 'chat' | 'query' | 'quality') => void
  toggleDarkMode: () => void
  toggleSidebar: () => void
  setProvider: (provider: 'ollama' | 'openai' | 'huggingface') => void
  setModel: (model: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  messages: [],
  isLoading: false,
  error: null,
  activeTab: 'chat',
  darkMode: false,
  sidebarOpen: true,
  selectedProvider: 'ollama',
  selectedModel: 'mistral',
  
  // Actions
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  
  clearMessages: () =>
    set({
      messages: [],
      error: null,
    }),
  
  setLoading: (loading) =>
    set({ isLoading: loading }),
  
  setError: (error) =>
    set({ error }),
  
  setActiveTab: (tab) =>
    set({ activeTab: tab }),
  
  toggleDarkMode: () =>
    set((state) => ({ darkMode: !state.darkMode })),
  
  toggleSidebar: () =>
    set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  setProvider: (provider) =>
    set({ selectedProvider: provider }),
  
  setModel: (model) =>
    set({ selectedModel: model }),
}))
