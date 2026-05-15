import { useQuery } from '@tanstack/react-query'
import { apiClient, HealthCheck } from '@/api/client'

export function useHealth() {
  return useQuery<HealthCheck>({
    queryKey: ['health'],
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30_000, // Poll every 30 seconds
    refetchIntervalInBackground: false,
  })
}
