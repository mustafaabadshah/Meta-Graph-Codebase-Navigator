import {
  Repository, ValidationResult, IndexStatus, GraphStatistics,
  SubgraphData, QueryResponse, SourceSnippet, SystemStatus,
  BenchmarkResult, QueryHistoryItem, GraphDiffSummary
} from '../types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      errorMsg = errorData.message || errorData.detail || errorMsg;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Health & System
  getSystemStatus: () => request<SystemStatus>('/system/status'),
  getHealth: () => request<{ status: string }>('/health'),
  switchGraphBackend: (backend: string) =>
    request<{ status: string; message: string; system: SystemStatus }>('/system/backend', {
      method: 'POST',
      body: JSON.stringify({ backend }),
    }),

  // Repositories
  listRepositories: () => request<Repository[]>('/repositories'),
  getRepository: (id: string) => request<Repository>(`/repositories/${id}`),
  registerRepository: (path: string, name?: string) =>
    request<Repository>('/repositories', {
      method: 'POST',
      body: JSON.stringify({ path, name }),
    }),
  validatePath: (path: string) =>
    request<ValidationResult>('/repositories', {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),
  deleteRepository: (id: string) =>
    request<{ status: string }>(`/repositories/${id}`, { method: 'DELETE' }),

  // Indexing
  startIndexing: (repoId: string) =>
    request<IndexStatus>(`/repositories/${repoId}/index`, { method: 'POST' }),
  reindex: (repoId: string) =>
    request<IndexStatus>(`/repositories/${repoId}/reindex`, { method: 'POST' }),
  getIndexStatus: (repoId: string) =>
    request<IndexStatus>(`/repositories/${repoId}/index-status`),
  getGraphDiff: (repoId: string) =>
    request<GraphDiffSummary>(`/repositories/${repoId}/diff`),
  getStatistics: (repoId: string) =>
    request<GraphStatistics>(`/repositories/${repoId}/statistics`),

  // Graph Exploration
  getGraph: (
    repoId: string,
    depth = 2,
    limit = 80,
    viewMode = 'architecture',
    focus?: string,
    diffFilter: 'all' | 'changes' | 'added' | 'modified' = 'all'
  ) => {
    let url = `/repositories/${repoId}/graph?depth=${depth}&limit=${limit}&view_mode=${encodeURIComponent(viewMode)}&diff_filter=${encodeURIComponent(diffFilter)}`;
    if (focus) url += `&focus=${encodeURIComponent(focus)}`;
    return request<SubgraphData>(url);
  },
  searchSymbols: (repoId: string, query: string, limit = 30) =>
    request<any[]>(`/repositories/${repoId}/symbols?q=${encodeURIComponent(query)}&limit=${limit}`),
  getSymbolDetails: (repoId: string, symbolId: string) =>
    request<any>(`/repositories/${repoId}/symbols/${encodeURIComponent(symbolId)}/details`),
  getSymbolRelationships: (repoId: string, symbolId: string) =>
    request<any>(`/repositories/${repoId}/symbols/${encodeURIComponent(symbolId)}/relationships`),
  getSourceSnippet: (repoId: string, file: string, start?: number, end?: number, symbol?: string) => {
    let q = `file=${encodeURIComponent(file)}`;
    if (start) q += `&start_line=${start}`;
    if (end) q += `&end_line=${end}`;
    if (symbol) q += `&symbol=${encodeURIComponent(symbol)}`;
    return request<SourceSnippet>(`/repositories/${repoId}/source?${q}`);
  },
  tracePaths: (repoId: string, sourceId: string, targetId: string, maxDepth = 4) =>
    request<{ paths: any[] }>(
      `/repositories/${repoId}/paths?source_id=${encodeURIComponent(sourceId)}&target_id=${encodeURIComponent(targetId)}&max_depth=${maxDepth}`
    ),

  // Query & Assistant
  askQuestion: (repoId: string, question: string, retrievalDepth = 3, detailLevel = 'detailed') =>
    request<QueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify({
        repository_id: repoId,
        question,
        retrieval_depth: retrievalDepth,
        detail_level: detailLevel,
      }),
    }),
  getQueryHistory: () => request<QueryHistoryItem[]>('/query/history'),

  // Evaluations
  listEvaluations: () => request<BenchmarkResult[]>('/evaluations'),
  runEvaluation: (repoId: string) =>
    request<BenchmarkResult>(`/evaluations/run?repository_id=${encodeURIComponent(repoId)}`, {
      method: 'POST',
    }),
  getBenchmarkQuestions: () => request<any[]>('/evaluations/questions'),
};
