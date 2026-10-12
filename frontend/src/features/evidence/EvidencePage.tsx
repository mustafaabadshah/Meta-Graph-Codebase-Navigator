import React, { useState, useEffect } from 'react';
import {
  FileCode2,
  Hash,
  Layers,
  Sparkles,
  RefreshCw,
  GitFork,
  CheckCircle2,
} from 'lucide-react';
import { Repository, SourceSnippet, Citation } from '../../types';
import { api } from '../../api/client';

interface EvidencePageProps {
  activeRepo: Repository | undefined;
  activeCitation?: Citation | null;
  onViewInGraph: (symbolId: string) => void;
}

export const EvidencePage: React.FC<EvidencePageProps> = ({
  activeRepo,
  activeCitation,
  onViewInGraph,
}) => {
  const [filePath, setFilePath] = useState(
    activeCitation?.file || 'backend/app/agents/groq_agent.py'
  );
  const [startLine, setStartLine] = useState<number | undefined>(
    activeCitation?.start_line ?? 59
  );
  const [endLine, setEndLine] = useState<number | undefined>(
    activeCitation?.end_line ?? 266
  );
  const [symbolName, setSymbolName] = useState<string | undefined>(
    activeCitation?.symbol ?? 'GroqChessAgent.select_move'
  );
  const [evidence, setEvidence] = useState<SourceSnippet | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (activeCitation) {
      setFilePath(activeCitation.file);
      setStartLine(activeCitation.start_line);
      setEndLine(activeCitation.end_line);
      setSymbolName(activeCitation.symbol || undefined);
    }
  }, [activeCitation]);

  const loadEvidence = async () => {
    if (!activeRepo || !filePath.trim()) return;
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await api.getSourceSnippet(
        activeRepo.id,
        filePath,
        startLine,
        endLine,
        symbolName
      );
      setEvidence(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to fetch source evidence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, [activeRepo?.id, filePath, startLine, endLine]);

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>Source Evidence Viewer</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
            Inspect authentic Python code from authorized repository paths with highlighted citation line bounds.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {symbolName && (
            <button
              className="btn-secondary"
              onClick={() => onViewInGraph(symbolName)}
            >
              <GitFork size={14} color="#06b6d4" />
              <span>Locate in Graph Explorer</span>
            </button>
          )}
          <button className="btn-secondary" onClick={loadEvidence} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Reload File</span>
          </button>
        </div>
      </div>

      {/* Target File Header Card */}
      <div className="glass-panel" style={{ padding: '18px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <FileCode2 size={20} color="#06b6d4" />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600 }}>
                {evidence?.rel_path || filePath}
              </div>
              {symbolName && (
                <div style={{ fontSize: '12px', color: '#38bdf8', marginTop: '2px' }}>
                  Target Symbol: <strong>{symbolName}</strong>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: 'var(--text-dim)' }}>
            {evidence && (
              <>
                <span className="badge badge-amber">
                  Highlighted Lines {evidence.start_line} - {evidence.end_line}
                </span>
                <span className="badge badge-cyan">{evidence.total_lines} Total Lines</span>
                <span style={{ fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Hash size={13} />
                  SHA: {evidence.file_hash.slice(0, 10)}...
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {errorMsg && (
        <div style={{ color: '#fb7185', background: 'rgba(244,63,94,0.1)', padding: '12px', borderRadius: '8px' }}>
          {errorMsg}
        </div>
      )}

      {/* Code Snippet Box */}
      {evidence && (
        <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
          <div
            style={{
              padding: '12px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              background: 'rgba(0,0,0,0.2)',
              fontSize: '12px',
              color: 'var(--text-muted)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>Verified Source Snippet</span>
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={13} /> Strict Provenance
            </span>
          </div>

          <div className="code-container" style={{ margin: 0, borderRadius: 0, border: 'none', maxHeight: '650px' }}>
            <pre style={{ margin: 0 }}>
              {evidence.snippet.split('\n').map((line, idx) => {
                const lineNumMatch = line.match(/^\s*(\d+)\s*\|/);
                const currentLineNum = lineNumMatch ? parseInt(lineNumMatch[1], 10) : -1;
                const isWithinCitation =
                  currentLineNum >= evidence.start_line && currentLineNum <= evidence.end_line;

                return (
                  <div
                    key={idx}
                    className={isWithinCitation ? 'citation-highlight' : ''}
                    style={{ padding: '2px 8px' }}
                  >
                    {line}
                  </div>
                );
              })}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
