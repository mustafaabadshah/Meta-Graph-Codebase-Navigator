import React from 'react';
import { Database, Cpu, Sparkles, FolderGit2 } from 'lucide-react';
import { Repository, SystemStatus } from '../types';

interface NavbarProps {
  repositories: Repository[];
  activeRepoId: string;
  onSelectRepo: (id: string) => void;
  systemStatus: SystemStatus | null;
  onSwitchBackend?: (backend: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  repositories,
  activeRepoId,
  onSelectRepo,
  systemStatus,
  onSwitchBackend,
}) => {
  const activeRepo = repositories.find((r) => r.id === activeRepoId);
  const currentMode = systemStatus?.selection_mode || 'auto';
  const rawEngine = systemStatus?.active_engine || systemStatus?.graph_backend || 'Loading';

  const formatEngineName = (name: string) => {
    if (name.toLowerCase().includes('neo4j')) return 'Neo4j';
    if (name.toLowerCase().includes('redis')) return 'Redis';
    if (name.toLowerCase().includes('networkx')) return 'NetworkX';
    return name;
  };
  const activeEngine = formatEngineName(rawEngine);

  const isNeoConnected = systemStatus?.neo4j_connectivity?.connected ?? false;
  const isRedisConnected = systemStatus?.redis_connectivity?.connected ?? false;
  const isGraphConnected =
    currentMode === 'neo4j'
      ? isNeoConnected
      : currentMode === 'redis'
      ? isRedisConnected
      : isNeoConnected || isRedisConnected || true;

  const getBackendTooltip = () => {
    if (currentMode === 'auto') {
      return `Auto Selection: Serving via ${activeEngine}. Neo4j: ${isNeoConnected ? 'Online' : 'Offline'}, Redis Cache: ${isRedisConnected ? 'Active' : 'Offline'}, NetworkX: Ready`;
    }
    return `Manual Selection: ${currentMode.toUpperCase()} (Serving via ${activeEngine})`;
  };

  return (
    <header
      style={{
        height: '64px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(11, 15, 23, 0.95)',
        backdropFilter: 'blur(10px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        zIndex: 50,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(6, 182, 212, 0.4)',
            }}
          >
            <Sparkles size={18} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: 700, letterSpacing: '-0.3px', margin: 0 }}>
              Meta-Graph <span style={{ color: '#06b6d4' }}>Navigator</span>
            </h1>
            <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: 0 }}>
              Codebase Knowledge Graph & Reasoning
            </p>
          </div>
        </div>

        {/* Repository Switcher */}
        <div
          style={{
            marginLeft: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255, 255, 255, 0.04)',
            padding: '6px 12px',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <FolderGit2 size={15} color="#06b6d4" />
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Target:</span>
          <select
            value={activeRepoId}
            onChange={(e) => onSelectRepo(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-main)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id} style={{ background: '#121826' }}>
                {repo.name} {repo.commit_hash ? `(${repo.commit_hash.slice(0, 7)})` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Engine Status Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Graph Engine Switcher */}
        <div
          className="glass-panel"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            fontSize: '12px',
          }}
          title={getBackendTooltip()}
        >
          <Database size={14} color="#06b6d4" />
          <span style={{ color: 'var(--text-muted)' }}>Graph:</span>
          <select
            value={currentMode}
            onChange={(e) => onSwitchBackend && onSwitchBackend(e.target.value)}
            disabled={!onSwitchBackend}
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#f1f5f9',
              borderRadius: '6px',
              padding: '3px 8px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="auto" style={{ background: '#121826' }}>
              Auto (Neo4j / Redis / NX)
            </option>
            <option value="neo4j" style={{ background: '#121826' }}>
              Neo4j
            </option>
            <option value="redis" style={{ background: '#121826' }}>
              Redis
            </option>
            <option value="networkx" style={{ background: '#121826' }}>
              NetworkX
            </option>
          </select>

          {/* Active Serving Badge */}
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 7px',
              borderRadius: '8px',
              background: currentMode === 'auto' ? 'rgba(6, 182, 212, 0.15)' : 'rgba(99, 102, 241, 0.15)',
              color: currentMode === 'auto' ? '#38bdf8' : '#a5b4fc',
              border: `1px solid ${currentMode === 'auto' ? 'rgba(6, 182, 212, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
            }}
          >
            {activeEngine}
          </span>

          <span
            className="live-dot"
            style={{
              background: isGraphConnected ? '#10b981' : '#f59e0b',
              boxShadow: isGraphConnected ? '0 0 8px #10b981' : '0 0 8px #f59e0b',
            }}
          />
        </div>

        {/* Groq Model */}
        <div
          className="glass-panel"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            fontSize: '12px',
          }}
        >
          <Cpu size={14} color="#06b6d4" />
          <span style={{ color: 'var(--text-muted)' }}>LLM:</span>
          <span style={{ fontWeight: 600, color: '#38bdf8' }}>
            {systemStatus?.groq_model || (systemStatus?.groq_configured ? 'Groq Ready' : 'Deterministic')}
          </span>
          <span
            className="live-dot"
            style={{
              background: systemStatus?.groq_configured ? '#06b6d4' : '#a855f7',
              boxShadow: systemStatus?.groq_configured ? '0 0 8px #06b6d4' : '0 0 8px #a855f7',
            }}
          />
        </div>
      </div>
    </header>
  );
};
