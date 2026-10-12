import React from 'react';
import { Database, Cpu, Sparkles, FolderGit2 } from 'lucide-react';
import { Repository, SystemStatus } from '../types';

interface NavbarProps {
  repositories: Repository[];
  activeRepoId: string;
  onSelectRepo: (id: string) => void;
  systemStatus: SystemStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  repositories,
  activeRepoId,
  onSelectRepo,
  systemStatus,
}) => {
  const activeRepo = repositories.find((r) => r.id === activeRepoId);
  const isNeo4j = systemStatus?.graph_backend === 'neo4j';
  const isGraphConnected = systemStatus?.graph_details?.connected ?? false;

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
        {/* Graph Backend */}
        <div
          className="glass-panel"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            fontSize: '12px',
          }}
          title={
            isNeo4j
              ? `Connected to Neo4j (${systemStatus?.neo4j_connectivity?.message || 'Ready'})`
              : `Using NetworkX graph engine (${systemStatus?.graph_details?.message || 'Ready'})`
          }
        >
          <Database size={14} color={isGraphConnected ? '#10b981' : '#f59e0b'} />
          <span style={{ color: 'var(--text-muted)' }}>Graph:</span>
          <span style={{ fontWeight: 600, color: '#f1f5f9' }}>
            {systemStatus?.graph_backend.toUpperCase() || 'LOADING'}
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
