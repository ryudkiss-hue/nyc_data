import axios, { AxiosInstance, AxiosError } from 'axios'

// --- Request types ---

export interface ChatRequest {
  message: string
  dataset_id?: string
  provider?: string
  model?: string
}

export interface QueryRequest {
  question: string
  max_results?: number
  explain?: boolean
  provider?: string
  model?: string
}

// --- Response types ---

export interface ChatResponse {
  response: string
  message_id: string
  history_length: number
  timestamp: string
}

export interface QueryResult {
  sql_query: string
  results: Record<string, unknown>[]
  row_count: number
  interpretation?: string
  execution_time_ms: number
  timestamp: string
}

export interface HealthCheck {
  status: string
  chatbot: boolean
  query_engine: boolean
  database: boolean
  timestamp: string
}

// --- API Client ---

class APIClient {
  private client: AxiosInstance

  constructor(baseURL = '/api/v1/llm') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30_000,
    })

    // Centralised error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<{ detail?: string }>) => {
        const message =
          error.response?.data?.detail ??
          error.message ??
          'An unexpected error occurred'
        return Promise.reject(new Error(message))
      }
    )
  }

  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    const { data } = await this.client.post<ChatResponse>('/chat', request)
    return data
  }

  async getChatHistory(limit = 10): Promise<ChatResponse[]> {
    const { data } = await this.client.get<ChatResponse[]>('/chat/history', {
      params: { limit },
    })
    return data
  }

  async clearChatHistory(): Promise<void> {
    await this.client.post('/chat/clear')
  }

  async getSuggestedAnalyses(datasetId: string): Promise<string[]> {
    const { data } = await this.client.post<string[]>('/chat/suggest-analyses', null, {
      params: { dataset_id: datasetId },
    })
    return data
  }

  async executeQuery(request: QueryRequest): Promise<QueryResult> {
    const { data } = await this.client.post<QueryResult>('/query', request)
    return data
  }

  async executeQueryInSession(
    sessionId: string,
    request: QueryRequest
  ): Promise<QueryResult> {
    const { data } = await this.client.post<QueryResult>(
      `/query/session/${sessionId}`,
      request
    )
    return data
  }

  async getSchema(): Promise<Record<string, unknown>> {
    const { data } = await this.client.get<Record<string, unknown>>('/query/schema')
    return data
  }

  async assessQualityIssue(description: string): Promise<Record<string, unknown>> {
    const { data } = await this.client.post<Record<string, unknown>>('/quality/assess', {
      description,
    })
    return data
  }

  async suggestMetrics(datasetId: string): Promise<Record<string, unknown>> {
    const { data } = await this.client.get<Record<string, unknown>>('/analytics/suggest-metrics', {
      params: { dataset_id: datasetId },
    })
    return data
  }

  async getHealth(): Promise<HealthCheck> {
    const { data } = await this.client.get<HealthCheck>('/health')
    return data
  }
}

export const apiClient = new APIClient()
