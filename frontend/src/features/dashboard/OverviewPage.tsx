import React, { useEffect, useState } from 'react';
import {
  FileCode,
  Layers,
  Network,
  Share2,
  Database,
  Cpu,
  ArrowRight,
  RefreshCw,
  Clock,
  Sparkles,
} from 'lucide-react';
import { Repository, GraphStatistics, SystemStatus, QueryHistoryItem } from '../../types';
import { api } from '../../api/client';
import { NavTab } from '../../components/Sidebar';

interface OverviewPageProps {
  activeRepo: Repository | undefined;
  systemStatus: SystemStatus | null;
  onNavigate: (tab: NavTab) => void;
  onSwitchBackend?: (backend: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  activeRepo,
  systemStatus,
  onNavigate,
  onSwitchBackend,
}) => {
  const [stats, setStats] = useState<GraphStatistics | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);

  const fetchStats = async () => {
    if (!activeRepo) return;
    try {
      setLoading(true);
      const data = await api.getStatistics(activeRepo.id);
      setStats(data);
      const hist = await api.getQueryHistory();
      setHistory(hist);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [activeRepo?.id]);

  const handleBackendClick = async (mode: string) => {
    if (!onSwitchBackend || switching) return;
    setSwitching(true);
    try {
      await onSwitchBackend(mode);
    } finally {
      setSwitching(false);
    }
  };

  const currentMode = systemStatus?.selection_mode || 'auto';
  const activeEngine = systemStatus?.active_engine || systemStatus?.graph_backend || 'NetworkX';
  const isNeoConnected = systemStatus?.neo4j_connectivity?.connected ?? false;
  const isRedisConnected = systemStatus?.redis_connectivity?.connected ?? false;
  const redisKeys = systemStatus?.redis_connectivity?.cached_keys ?? 0;

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '28px',
          background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(99, 102, 241, 0.05))',
          borderColor: 'rgba(6, 182, 212, 0.2)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span className="badge badge-cyan">Active Knowledge Graph</span>
            {activeRepo?.commit_hash && (
              <span className="badge badge-purple">
                Git Commit: {activeRepo.commit_hash.slice(0, 8)}
              </span>
            )}
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, letterSpacing: '-0.4px', margin: 0 }}>
            {activeRepo?.name || 'No Repository Selected'}
          </h2>
          <p
            style={{
              fontSize: '13px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              marginTop: '4px',
            }}
          >
            {activeRepo?.path || 'Configure a local Python directory in Repository Management.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn-secondary" onClick={fetchStats} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button className="btn-primary" onClick={() => onNavigate('assistant')}>
            <Sparkles size={16} />
            <span>Ask Architecture</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '20px',
        }}
      >
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: 500,
            }}
          >
            <span>Python Files</span>
            <FileCode size={18} color="#06b6d4" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700, marginTop: '12px', color: '#f1f5f9' }}>
            {stats?.nodes_by_type?.File ?? activeRepo?.file_count ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Scanned & Parsed with AST
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: 500,
            }}
          >
            <span>Classes & Methods</span>
            <Layers size={18} color="#8b5cf6" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700, marginTop: '12px', color: '#f1f5f9' }}>
            {(stats?.nodes_by_type?.Class ?? 0) + (stats?.nodes_by_type?.Function ?? 0)}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {stats?.nodes_by_type?.Class ?? 0} classes, {stats?.nodes_by_type?.Function ?? 0} functions
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: 500,
            }}
          >
            <span>Knowledge Graph Nodes</span>
            <Network size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700, marginTop: '12px', color: '#f1f5f9' }}>
            {stats?.total_nodes ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Entities in structural graph
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '22px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: 'var(--text-muted)',
              fontSize: '13px',
              fontWeight: 500,
            }}
          >
            <span>Direct Call Edges</span>
            <Share2 size={18} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 700, marginTop: '12px', color: '#f1f5f9' }}>
            {stats?.edges_by_type?.CALLS ?? 0}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {stats?.total_edges ?? 0} total structural edges
          </div>
        </div>
      </div>

      {/* Middle Row: Quick Actions & Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Graph Engine Status */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3
              style={{
                fontSize: '16px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                margin: 0,
              }}
            >
              <Database size={18} color="#06b6d4" />
              Graph Storage Diagnostics
            </h3>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: currentMode === 'auto' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                color: currentMode === 'auto' ? '#38bdf8' : '#a5b4fc',
                fontWeight: 600,
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              Mode: {currentMode.toUpperCase()}
            </span>
          </div>

          {/* Runtime Backend Switcher Segmented Control */}
          <div
            style={{
              display: 'flex',
              background: 'rgba(255, 255, 255, 0.03)',
              padding: '4px',
              borderRadius: '8px',
              gap: '4px',
              marginBottom: '16px',
              border: '1px solid var(--border-subtle)',
            }}
          >
            {[
              { id: 'auto', label: 'Auto (Intelligent)' },
              { id: 'neo4j', label: 'Neo4j' },
              { id: 'redis', label: 'Redis' },
              { id: 'networkx', label: 'NetworkX' },
            ].map((btn) => {
              const isSelected = currentMode === btn.id;
              return (
                <button
                  key={btn.id}
                  onClick={() => handleBackendClick(btn.id)}
                  disabled={switching || !onSwitchBackend}
                  style={{
                    flex: 1,
                    padding: '6px 8px',
                    fontSize: '11px',
                    fontWeight: isSelected ? 700 : 500,
                    borderRadius: '6px',
                    border: 'none',
                    cursor: switching ? 'wait' : 'pointer',
                    background: isSelected
                      ? 'linear-gradient(135deg, rgba(6, 182, 212, 0.25), rgba(99, 102, 241, 0.25))'
                      : 'transparent',
                    color: isSelected ? '#38bdf8' : 'var(--text-muted)',
                    boxShadow: isSelected ? '0 0 8px rgba(6, 182, 212, 0.2)' : 'none',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {btn.label}
                </button>
              );
            })}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Serving Engine</span>
              <span style={{ fontWeight: 600, color: '#38bdf8' }}>
                {activeEngine}
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Neo4j Cluster (7687)</span>
              <span
                style={{
                  color: isNeoConnected ? '#34d399' : '#fbbf24',
                  fontWeight: 600,
                }}
              >
                {isNeoConnected ? 'Online & Synced' : 'Offline (Skipped)'}
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Redis L1 Cache & Store (6379)</span>
              <span
                style={{
                  color: isRedisConnected ? '#34d399' : '#fbbf24',
                  fontWeight: 600,
                }}
              >
                {isRedisConnected ? `Connected (${redisKeys} keys cached)` : 'Offline'}
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>NetworkX AST Store</span>
              <span style={{ color: '#34d399', fontWeight: 600 }}>
                Ready (MultiDiGraph)
              </span>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.03)',
                borderRadius: '8px',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>LLM Grounding Engine</span>
              <span style={{ color: '#a78bfa', fontWeight: 600 }}>
                {systemStatus?.groq_model || 'Groq Active'}
              </span>
            </div>

            {systemStatus?.neo4j_connectivity?.troubleshooting && (
              <div
                style={{
                  fontSize: '12px',
                  color: 'var(--text-dim)',
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.2)',
                  padding: '10px',
                  borderRadius: '6px',
                }}
              >
                💡 {systemStatus.neo4j_connectivity.troubleshooting}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3
            style={{
              fontSize: '16px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '16px',
            }}
          >
            <Cpu size={18} color="#8b5cf6" />
            Quick Exploration
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              className="btn-secondary"
              onClick={() => onNavigate('assistant')}
              style={{ justifyContent: 'space-between', width: '100%' }}
            >
              <span>Ask "How does Groq rate limit handling work?"</span>
              <ArrowRight size={15} />
            </button>

            <button
              className="btn-secondary"
              onClick={() => onNavigate('graph')}
              style={{ justifyContent: 'space-between', width: '100%' }}
            >
              <span>Explore Interactive Subgraph in React Flow</span>
              <ArrowRight size={15} />
            </button>

            <button
              className="btn-secondary"
              onClick={() => onNavigate('evaluations')}
              style={{ justifyContent: 'space-between', width: '100%' }}
            >
              <span>Run Automated Benchmark Evaluation</span>
              <ArrowRight size={15} />
            </button>

            <button
              className="btn-secondary"
              onClick={() => onNavigate('repositories')}
              style={{ justifyContent: 'space-between', width: '100%' }}
            >
              <span>Manage Registered Repositories</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Recent Queries Activity Feed */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3
          style={{
            fontSize: '16px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px',
          }}
        >
          <Clock size={18} color="#10b981" />
          Recent Query Activity
        </h3>

        {history.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontSize: '13px', padding: '12px 0' }}>
            No recent questions asked yet. Try asking your first question in the AI Assistant!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {history.slice(0, 5).map((h, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Sparkles size={15} color="#06b6d4" />
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>{h.question}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px' }}>
                  <span className="badge badge-cyan">{h.citations_count} Citations</span>
                  <span style={{ color: 'var(--text-dim)' }}>{h.latency_ms} ms</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
