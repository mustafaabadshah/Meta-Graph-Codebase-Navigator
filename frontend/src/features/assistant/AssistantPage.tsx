import React, { useState } from 'react';
import {
  Send,
  Sparkles,
  Sliders,
  Copy,
  Check,
  FileCode2,
  AlertTriangle,
  GitFork,
  Clock,
  Layers,
} from 'lucide-react';
import { Repository, QueryResponse, Citation } from '../../types';
import { api } from '../../api/client';

interface AssistantPageProps {
  activeRepo: Repository | undefined;
  onOpenCitation: (citation: Citation) => void;
  onViewInGraph: (subgraph: any) => void;
}

export const AssistantPage: React.FC<AssistantPageProps> = ({
  activeRepo,
  onOpenCitation,
  onViewInGraph,
}) => {
  const [question, setQuestion] = useState(
    'How does the application handle a Groq API rate limit when an agent is playing a tournament? Trace the execution path, identify retry and exception-handling logic, explain what happens when retries are exhausted, and cite every relevant file, function, and line number.'
  );
  const [depth, setDepth] = useState(3);
  const [detailLevel, setDetailLevel] = useState('detailed');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const suggestedQuestions = [
    {
      title: 'Groq API Rate Limit & Fallback',
      text: 'How does the application handle a Groq API rate limit when an agent is playing a tournament? Trace the execution path, identify retry and exception-handling logic, explain what happens when retries are exhausted, and cite every relevant file, function, and line number.',
    },
    {
      title: 'Move Legality & Correction',
      text: 'How is chess move validation performed and how does the agent recover when an illegal move is proposed by the LLM?',
    },
    {
      title: 'Tournament Bracket Flow',
      text: 'Explain how TournamentService sets up tournament bracket matches and transitions into game execution.',
    },
    {
      title: 'Emergency Fallback Strategy',
      text: 'What logic does _select_emergency_move use when API attempts are exhausted?',
    },
  ];

  const handleAsk = async (queryText?: string) => {
    const q = queryText || question;
    if (!q.trim() || !activeRepo) return;

    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await api.askQuestion(activeRepo.id, q, depth, detailLevel);
      setResponse(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to generate architectural answer');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (response?.answer) {
      navigator.clipboard.writeText(response.answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>AI Architecture Assistant</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
          Ask multi-hop questions grounded in verified static AST graph traversals and authentic source code citations.
        </p>
      </div>

      {/* Suggested Questions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)' }}>
          Grounded Architecture Questions (Agent Chess):
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {suggestedQuestions.map((sq, i) => (
            <button
              key={i}
              className="btn-secondary"
              onClick={() => {
                setQuestion(sq.text);
                handleAsk(sq.text);
              }}
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.03)',
              }}
            >
              <Sparkles size={13} color="#06b6d4" />
              <span>{sq.title}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Question Input Box */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="Ask an architectural question about control flow, retry logic, or module interactions..."
            style={{
              width: '100%',
              background: 'rgba(0,0,0,0.3)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '12px 14px',
              color: '#fff',
              fontSize: '14px',
              lineHeight: 1.5,
              resize: 'vertical',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            {/* Traversal Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={15} color="var(--text-dim)" />
                <span style={{ color: 'var(--text-muted)' }}>Graph Depth:</span>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={depth}
                  onChange={(e) => setDepth(Number(e.target.value))}
                  style={{ width: '80px', accentColor: '#06b6d4' }}
                />
                <span style={{ fontWeight: 600, color: '#06b6d4' }}>{depth} Hops</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Detail:</span>
                <select
                  value={detailLevel}
                  onChange={(e) => setDetailLevel(e.target.value)}
                  style={{
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: '#fff',
                    padding: '4px 8px',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                >
                  <option value="detailed" style={{ background: '#121826' }}>Detailed Analysis</option>
                  <option value="concise" style={{ background: '#121826' }}>Concise Flow</option>
                </select>
              </div>
            </div>

            <button
              className="btn-primary"
              onClick={() => handleAsk()}
              disabled={loading || !question.trim()}
            >
              <Send size={15} />
              <span>{loading ? 'Synthesizing...' : 'Execute Retrieval'}</span>
            </button>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div
          style={{
            background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: '8px',
            padding: '12px 16px',
            color: '#fb7185',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <AlertTriangle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Answer Output Container */}
      {response && (
        <div className="glass-panel glow-border" style={{ padding: '28px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={18} color="#06b6d4" />
              <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Grounded Architectural Answer</h3>
              <span className="badge badge-green">Evidence Verified</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                className="btn-secondary"
                onClick={() => onViewInGraph(response.graph_subgraph)}
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                <GitFork size={14} color="#06b6d4" />
                <span>View Subgraph in Explorer</span>
              </button>

              <button
                className="btn-secondary"
                onClick={handleCopy}
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>

          {/* Formatted Markdown Content */}
          <div
            style={{
              fontSize: '14px',
              lineHeight: 1.7,
              color: '#e2e8f0',
              whiteSpace: 'pre-wrap',
              fontFamily: 'inherit',
            }}
          >
            {response.answer}
          </div>

          {/* Validated Citations Cards */}
          {response.citations.length > 0 && (
            <div style={{ marginTop: '16px', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileCode2 size={16} color="#06b6d4" />
                Verified Citations ({response.citations.length} Source References):
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                {response.citations.map((c, i) => (
                  <div
                    key={i}
                    onClick={() => onOpenCitation(c)}
                    className="glass-panel"
                    style={{
                      padding: '12px 14px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                      transition: 'all 0.2s ease',
                      border: '1px solid rgba(6, 182, 212, 0.2)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#38bdf8' }}>
                        {c.symbol || 'Source Snippet'}
                      </span>
                      <span className="badge badge-cyan">Lines {c.start_line}-{c.end_line}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      {c.file}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Telemetry Footer */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '20px',
              marginTop: '12px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '12px',
              color: 'var(--text-dim)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={14} />
              <span>Latency: <strong>{response.model_metadata.latency_ms ?? 0} ms</strong></span>
            </div>
            {response.model_metadata.model && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layers size={14} />
                <span>Model: <strong>{response.model_metadata.model}</strong></span>
              </div>
            )}
            {response.model_metadata.prompt_tokens ? (
              <div>Tokens: {response.model_metadata.prompt_tokens} in / {response.model_metadata.completion_tokens} out</div>
            ) : null}
            <div>Repository: <strong>{response.repository_id}</strong></div>
          </div>
        </div>
      )}
    </div>
  );
};
