import axios, { AxiosInstance } from 'axios'

interface ChatRequest {
  message: string
  dataset_id?: string
  provider?: string
  model?: string
}

interface ChatResponse {
  response: string
  message_id: string
  history_length: number
  timestamp: string
}

interface QueryRequest {
  question: string
  max_results?: number
  explain?: boolean
  provider?: string
  model?: string
}

interface QueryResult {
  sql_query: string
  results: Record<string, any>[]
  row_count: number
  interpretation?: string
  execution_time_ms: number
  timestamp: string
}

interface HealthCheck {
  status: string
  chatbot: boolean
  query_engine: boolean
  database: boolean
  timestamp: string
}

class APIClient {
  private client: AxiosInstance

  constructor(baseURL = '/api/v1/llm') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await this.client.post<ChatResponse>('/chat', request)
    return response.data
  }

  async getChatHistory(limit = 10): Promise<any> {
    const response = await this.client.get('/chat/history', {
      params: { limit },
    })
    return response.data
  }

  async clearChatHistory(): Promise<any> {
    const response = await this.client.post('/chat/clear')
    return response.data
  }

  async getSuggestedAnalyses(datasetId: string): Promise<any> {
    const response = await this.client.post('/chat/suggest-analyses', null, {
      params: { dataset_id: datasetId },
    })
    return response.data
  }

  async executeQuery(request: QueryRequest): Promise<QueryResult> {
    const response = await this.client.post<QueryResult>('/query', request)
    return response.data
  }

  async executeQueryInSession(
    sessionId: string,
    request: QueryRequest
  ): Promise<QueryResult> {
    const response = await this.client.post<QueryResult>(
      `/query/session/${sessionId}`,
      request
    )
    return response.data
  }

  async getSchema(): Promise<any> {
    const response = await this.client.get('/query/schema')
    return response.data
  }

  async assessQualityIssue(description: string): Promise<any> {
    const response = await this.client.post('/quality/assess', {
      description,
    })
    return response.data
  }

  async suggestMetrics(datasetId: string): Promise<any> {
    const response = await this.client.get('/analytics/suggest-metrics', {
      params: { dataset_id: datasetId },
    })
    return response.data
  }

  async getHealth(): Promise<HealthCheck> {
    const response = await this.client.get<HealthCheck>('/health')
    return response.data
  }
}

export const apiClient = new APIClient()
export type { ChatResponse, QueryResult, HealthCheck }
