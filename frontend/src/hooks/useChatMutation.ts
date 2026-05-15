import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useAppStore, Message } from '@/store/store'

interface ChatInput {
  message: string
  provider: string
  model: string
}

export function useChatMutation() {
  const addMessage = useAppStore((s) => s.addMessage)

  return useMutation({
    mutationFn: async (input: ChatInput) => {
      // Add user message optimistically
      const userMessage: Message = {
        id: `msg_${Date.now()}_user`,
        role: 'user',
        content: input.message,
        timestamp: new Date().toISOString(),
      }
      addMessage(userMessage)

      return apiClient.sendChatMessage({
        message: input.message,
        provider: input.provider,
        model: input.model,
      })
    },
    onSuccess: (response) => {
      const assistantMessage: Message = {
        id: response.message_id,
        role: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
      }
      addMessage(assistantMessage)
    },
    onError: (error) => {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to send message'
      const errorMsg: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: `Error: ${errorMessage}`,
        timestamp: new Date().toISOString(),
      }
      addMessage(errorMsg)
    },
  })
}
