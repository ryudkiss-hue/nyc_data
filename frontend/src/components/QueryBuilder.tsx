import React, { useState, useCallback } from 'react'
import { useAppStore } from '@/store/store'
import { useQueryMutation } from '@/hooks/useQueryMutation'
import { Loader, AlertCircle, Database, Copy, CheckCircle } from 'lucide-react'

export const QueryBuilder: React.FC = () => {
  const selectedProvider = useAppStore((s) => s.selectedProvider)
  const selectedModel = useAppStore((s) => s.selectedModel)

  const queryMutation = useQueryMutation()

  const [question, setQuestion] = useState('')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const handleExecuteQuery = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!question.trim() || queryMutation.isPending) return

      queryMutation.mutate({
        question,
        provider: selectedProvider,
        model: selectedModel,
      })
    },
    [question, queryMutation, selectedProvider, selectedModel]
  )

  const copyToClipboard = useCallback((text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }, [])

  const result = queryMutation.data

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">SQL Query Builder</h2>
        <p className="text-sm text-gray-600">
          Ask natural language questions and get SQL queries
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-4">
          {/* Input Form */}
          <form onSubmit={handleExecuteQuery} className="space-y-4 mb-6">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question in natural language... e.g., 'How many potholes in Manhattan?'"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nycblue-500 resize-none"
              rows={3}
              disabled={queryMutation.isPending}
              aria-label="Natural language query input"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-nycblue-500 text-white hover:bg-nycblue-600 rounded-lg transition disabled:opacity-50 flex items-center gap-2"
              disabled={queryMutation.isPending || !question.trim()}
            >
              {queryMutation.isPending && <Loader className="w-4 h-4 animate-spin" />}
              Execute Query
            </button>
          </form>

          {/* Error Message */}
          {queryMutation.isError && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-900">Error</h4>
                  <p className="text-sm text-red-700">
                    {queryMutation.error instanceof Error
                      ? queryMutation.error.message
                      : 'Failed to execute query'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4 animate-fadeIn">
              {/* SQL Query */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900 flex items-center gap-2">
                    <Database className="w-4 h-4" />
                    Generated SQL
                  </h4>
                  <button
                    onClick={() => copyToClipboard(result.sql_query, 'sql')}
                    className="p-1 hover:bg-gray-200 rounded transition"
                    aria-label="Copy SQL to clipboard"
                  >
                    {copiedId === 'sql' ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-600" />
                    )}
                  </button>
                </div>
                <pre className="bg-white p-3 rounded border border-gray-200 overflow-x-auto text-xs text-gray-700">
                  <code>{result.sql_query}</code>
                </pre>
              </div>

              {/* Execution Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-sm text-gray-600">Rows Returned</p>
                  <p className="text-2xl font-bold text-nycblue-600">{result.row_count}</p>
                </div>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-sm text-gray-600">Execution Time</p>
                  <p className="text-2xl font-bold text-green-600">
                    {result.execution_time_ms.toFixed(1)}ms
                  </p>
                </div>
              </div>

              {/* Interpretation */}
              {result.interpretation && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Interpretation</h4>
                  <p className="text-sm text-gray-700">{result.interpretation}</p>
                </div>
              )}

              {/* Results Table */}
              {result.results && result.results.length > 0 && (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <h4 className="font-medium text-gray-900">
                      Results (showing {Math.min(result.results.length, 10)} of {result.row_count})
                    </h4>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200">
                          {Object.keys(result.results[0]).map((key) => (
                            <th
                              key={key}
                              className="px-4 py-2 text-left font-medium text-gray-700"
                            >
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.results.slice(0, 10).map((row, idx) => (
                          <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                            {Object.values(row).map((value, colIdx) => (
                              <td key={colIdx} className="px-4 py-2 text-gray-700">
                                {value !== null && value !== undefined ? String(value) : '—'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Loading State */}
          {queryMutation.isPending && (
            <div className="flex justify-center items-center py-12">
              <div className="text-center">
                <Loader className="w-8 h-8 animate-spin text-nycblue-500 mx-auto mb-3" />
                <p className="text-gray-600">Executing query...</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!queryMutation.isPending && !result && !queryMutation.isError && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <Database className="w-12 h-12 mb-3 opacity-50" />
              <p className="text-center">Ask a question to get started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
