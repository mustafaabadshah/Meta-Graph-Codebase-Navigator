import React, { useState, useEffect } from 'react';
import {
  Award,
  Play,
  CheckCircle2,
  Clock,
  Target,
  FileCheck,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { Repository, BenchmarkResult } from '../../types';
import { api } from '../../api/client';

interface EvaluationsPageProps {
  activeRepo: Repository | undefined;
}

export const EvaluationsPage: React.FC<EvaluationsPageProps> = ({ activeRepo }) => {
  const [runs, setRuns] = useState<BenchmarkResult[]>([]);
  const [running, setRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<BenchmarkResult | null>(null);

  const fetchRuns = async () => {
    try {
      const data = await api.listEvaluations();
      setRuns(data);
      if (data.length > 0 && !currentRun) {
        setCurrentRun(data[0]);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleRunBenchmark = async () => {
    if (!activeRepo) return;
    try {
      setRunning(true);
      const res = await api.runEvaluation(activeRepo.id);
      setCurrentRun(res);
      await fetchRuns();
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>Evaluation & Benchmarking</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
            Empirical benchmarking of graph retrieval precision, file accuracy, citation line validity, and latency.
          </p>
        </div>

        <button className="btn-primary" onClick={handleRunBenchmark} disabled={running}>
          <Play size={15} />
          <span>{running ? 'Running Benchmark...' : 'Run Benchmark Suite'}</span>
        </button>
      </div>

      {/* Benchmark Scorecards */}
      {currentRun && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '18px' }}>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span>Symbol Hit Rate</span>
              <Target size={16} color="#06b6d4" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, marginTop: '8px', color: '#38bdf8' }}>
              {currentRun.symbol_retrieval_hit_rate_pct}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Ground truth symbols resolved
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span>File Retrieval Accuracy</span>
              <FileCheck size={16} color="#8b5cf6" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, marginTop: '8px', color: '#a78bfa' }}>
              {currentRun.relevant_file_accuracy_pct}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Expected file paths cited
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span>Citation Line Validity</span>
              <CheckCircle2 size={16} color="#10b981" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, marginTop: '8px', color: '#34d399' }}>
              {currentRun.citation_validity_pct}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Lines verified in source repo
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '12px' }}>
              <span>Average Latency</span>
              <Clock size={16} color="#f59e0b" />
            </div>
            <div style={{ fontSize: '28px', fontWeight: 700, marginTop: '8px', color: '#fbbf24' }}>
              {currentRun.average_latency_ms} ms
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              End-to-end traversal + LLM
            </div>
          </div>
        </div>
      )}

      {/* Evaluated Questions Breakdown */}
      {currentRun && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px' }}>
            Benchmark Test Cases ({currentRun.results.length} Questions)
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {currentRun.results.map((r, idx) => (
              <div
                key={idx}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div>
                    <span className="badge badge-cyan" style={{ marginBottom: '6px' }}>{r.category}</span>
                    <h4 style={{ fontSize: '14px', fontWeight: 600, margin: 0 }}>{r.question}</h4>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span className="badge badge-green">{r.symbol_hit_rate * 100}% Symbol Hit</span>
                    <span className="badge badge-purple">{r.file_hit_rate * 100}% File Match</span>
                  </div>
                </div>

                <div
                  style={{
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    background: 'rgba(0,0,0,0.3)',
                    padding: '10px',
                    borderRadius: '6px',
                    marginTop: '8px',
                    lineHeight: 1.5,
                  }}
                >
                  {r.answer_snippet}
                </div>

                <div style={{ display: 'flex', gap: '16px', marginTop: '10px', fontSize: '11px', color: 'var(--text-dim)' }}>
                  <div>Citations: <strong>{r.citations_count}</strong></div>
                  <div>Latency: <strong>{r.latency_ms} ms</strong></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical Runs */}
      {runs.length > 0 && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Historical Benchmark Runs</h4>
          <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '6px' }}>
            {runs.map((r) => (
              <button
                key={r.run_id}
                className={`btn-secondary ${currentRun?.run_id === r.run_id ? 'glow-border' : ''}`}
                onClick={() => setCurrentRun(r)}
                style={{ fontSize: '12px', padding: '8px 12px' }}
              >
                <div>Run: {new Date(r.timestamp).toLocaleTimeString()}</div>
                <div style={{ color: '#06b6d4', fontWeight: 600 }}>{r.symbol_retrieval_hit_rate_pct}% Hits</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
