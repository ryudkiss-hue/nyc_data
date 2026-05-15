import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface AppState {
  // Chat state (conversation history is UI state)
  messages: Message[]

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
  setActiveTab: (tab: 'chat' | 'query' | 'quality') => void
  toggleDarkMode: () => void
  toggleSidebar: () => void
  setProvider: (provider: 'ollama' | 'openai' | 'huggingface') => void
  setModel: (model: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  messages: [],
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
    set({ messages: [] }),

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
