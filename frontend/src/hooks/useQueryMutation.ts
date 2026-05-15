import { useMutation } from '@tanstack/react-query'
import { apiClient, QueryResult } from '@/api/client'

interface QueryInput {
  question: string
  maxResults?: number
  explain?: boolean
  provider: string
  model: string
}

export function useQueryMutation() {
  return useMutation<QueryResult, Error, QueryInput>({
    mutationFn: (input) =>
      apiClient.executeQuery({
        question: input.question,
        max_results: input.maxResults ?? 100,
        explain: input.explain ?? true,
        provider: input.provider,
        model: input.model,
      }),
  })
}
