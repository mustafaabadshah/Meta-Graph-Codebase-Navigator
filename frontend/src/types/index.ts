export interface Repository {
  id: string;
  name: string;
  path: string;
  is_valid: boolean;
  commit_hash?: string | null;
  indexed_at?: string | null;
  file_count?: number;
  warnings?: string[];
}

export interface ValidationResult {
  path: string;
  is_valid: boolean;
  exists: boolean;
  is_directory: boolean;
  is_git: boolean;
  commit_hash?: string | null;
  estimated_python_files: number;
  message: string;
}

export interface IndexStatus {
  repository_id: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  current_file?: string | null;
  scanned_files: number;
  indexed_files: number;
  failed_files: number;
  total_files: number;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  warnings?: string[];
}

export interface GraphStatistics {
  repository_id: string;
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

export interface GraphNode {
  id: string;
  type: string;
  name: string;
  qualified_name?: string;
  rel_path?: string;
  start_line?: number;
  end_line?: number;
  docstring?: string;
  is_async?: boolean;
  is_method?: boolean;
  parameters?: string[];
  repo_id?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, any>;
}

export interface SubgraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Citation {
  repository: string;
  file: string;
  symbol?: string | null;
  start_line: number;
  end_line: number;
  evidence_type?: string;
}

export interface QueryResponse {
  repository_id: string;
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_symbols: any[];
  graph_subgraph: SubgraphData;
  execution_flow: string[];
  warnings: string[];
  model_metadata: {
    model?: string;
    attempts?: number;
    latency_ms?: number;
    prompt_tokens?: number;
    completion_tokens?: number;
    provider?: string;
    status?: string;
    warning?: string;
  };
}

export interface QueryHistoryItem {
  timestamp: string;
  repository_id: string;
  question: string;
  citations_count: number;
  model: string;
  latency_ms: number;
}

export interface SourceSnippet {
  repository_id: string;
  rel_path: string;
  symbol?: string | null;
  start_line: number;
  end_line: number;
  total_lines: number;
  snippet: string;
  full_content?: string | null;
  file_hash: string;
}

export interface SystemStatus {
  status: string;
  version: string;
  graph_backend: string;
  active_engine?: string;
  selection_mode?: string;
  available_backends?: string[];
  graph_details?: Record<string, any>;
  neo4j_connectivity?: {
    connected: boolean;
    message?: string;
    troubleshooting?: string;
  };
  redis_connectivity?: {
    connected: boolean;
    url?: string;
    cached_keys?: number;
  };
  networkx_connectivity?: {
    connected: boolean;
    active?: boolean;
  };
  groq_configured: boolean;
  groq_model?: string | null;
}

export interface BenchmarkResult {
  run_id: string;
  timestamp: string;
  repository_id: string;
  total_questions: number;
  symbol_retrieval_hit_rate_pct: number;
  relevant_file_accuracy_pct: number;
  citation_validity_pct: number;
  average_latency_ms: number;
  results: {
    question_id: string;
    category: string;
    question: string;
    symbol_hit_rate: number;
    file_hit_rate: number;
    citations_count: number;
    valid_citations: number;
    latency_ms: number;
    answer_snippet: string;
  }[];
}
