import React, { useState, useEffect } from 'react';
import {
  FolderPlus,
  Play,
  RotateCw,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Folder,
  Terminal,
} from 'lucide-react';
import { Repository, IndexStatus } from '../../types';
import { api } from '../../api/client';

interface RepositoriesPageProps {
  repositories: Repository[];
  activeRepoId: string;
  onSelectRepo: (id: string) => void;
  onRefreshRepos: () => void;
}

export const RepositoriesPage: React.FC<RepositoriesPageProps> = ({
  repositories,
  activeRepoId,
  onSelectRepo,
  onRefreshRepos,
}) => {
  const [newPath, setNewPath] = useState('E:\\MM Office\\Agent Chess');
  const [newName, setNewName] = useState('Agent Chess');
  const [isRegistering, setIsRegistering] = useState(false);
  const [indexStatus, setIndexStatus] = useState<Record<string, IndexStatus>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Poll status for running indexing jobs
  useEffect(() => {
    const timer = setInterval(async () => {
      for (const repo of repositories) {
        try {
          const status = await api.getIndexStatus(repo.id);
          setIndexStatus((prev) => ({ ...prev, [repo.id]: status }));
          if (status.status === 'completed' && (!repo.indexed_at || status.completed_at !== repo.indexed_at)) {
            onRefreshRepos();
          }
        } catch {
          // ignore
        }
      }
    }, 1500);

    return () => clearInterval(timer);
  }, [repositories]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    try {
      setIsRegistering(true);
      await api.registerRepository(newPath, newName);
      onRefreshRepos();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to register repository');
    } finally {
      setIsRegistering(false);
    }
  };

  const handleStartIndex = async (repoId: string, isReindex = false) => {
    try {
      if (isReindex) {
        await api.reindex(repoId);
      } else {
        await api.startIndexing(repoId);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to trigger indexing');
    }
  };

  const handleDelete = async (repoId: string) => {
    if (!window.confirm(`Are you sure you want to delete knowledge graph data for '${repoId}'?`)) {
      return;
    }
    try {
      await api.deleteRepository(repoId);
      onRefreshRepos();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to delete repository');
    }
  };

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>Repository Management</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px' }}>
          Register local Python repositories for static AST parsing, graph database ingestion, and bounded multi-hop retrieval.
        </p>
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

      {/* Register Repository Form */}
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
          <FolderPlus size={18} color="#06b6d4" />
          Register Local Repository
        </h3>

        <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '14px' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '6px',
                }}
              >
                Repository Display Name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Agent Chess"
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '9px 12px',
                  color: '#fff',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  marginBottom: '6px',
                }}
              >
                Canonical Directory Path
              </label>
              <input
                type="text"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                placeholder="E:\MM Office\Agent Chess"
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '9px 12px',
                  color: '#fff',
                  fontSize: '13px',
                  fontFamily: 'var(--font-mono)',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" className="btn-primary" disabled={isRegistering}>
              <FolderPlus size={16} />
              <span>{isRegistering ? 'Validating & Adding...' : 'Register Repository'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Registered Repositories List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>Registered Codebases</h3>

        {repositories.map((repo) => {
          const status = indexStatus[repo.id];
          const isRunning = status?.status === 'running';
          const isActive = repo.id === activeRepoId;

          return (
            <div
              key={repo.id}
              className={`glass-panel ${isActive ? 'glow-border' : ''}`}
              style={{ padding: '24px' }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Folder size={18} color="#06b6d4" />
                    <h4 style={{ fontSize: '17px', fontWeight: 700, margin: 0 }}>{repo.name}</h4>
                    {isActive && <span className="badge badge-cyan">Active Workspace</span>}
                    {status?.status === 'completed' && <span className="badge badge-green">Indexed</span>}
                    {isRunning && <span className="badge badge-amber">Indexing...</span>}
                  </div>
                  <div
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      marginTop: '6px',
                    }}
                  >
                    {repo.path}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  {!isActive && (
                    <button className="btn-secondary" onClick={() => onSelectRepo(repo.id)}>
                      Select Active
                    </button>
                  )}
                  <button
                    className="btn-primary"
                    onClick={() => handleStartIndex(repo.id, false)}
                    disabled={isRunning}
                  >
                    <Play size={14} />
                    <span>{isRunning ? 'Indexing...' : 'Index Codebase'}</span>
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => handleStartIndex(repo.id, true)}
                    disabled={isRunning}
                    title="Incremental Re-index changed files"
                  >
                    <RotateCw size={14} />
                    <span>Re-index</span>
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => handleDelete(repo.id)}
                    style={{ color: '#fb7185' }}
                    title="Delete Graph Data"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Live Indexing Progress Bar */}
              {isRunning && (
                <div
                  style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '14px',
                    borderRadius: '8px',
                    marginTop: '12px',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '12px',
                      marginBottom: '8px',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Terminal size={14} color="#06b6d4" />
                      Parsing: {status?.current_file || 'Scanning files...'}
                    </span>
                    <span style={{ fontWeight: 600, color: '#06b6d4' }}>
                      {status?.progress_percentage ?? 0}% ({status?.indexed_files ?? 0}/{status?.total_files ?? 0} files)
                    </span>
                  </div>
                  <div
                    style={{
                      width: '100%',
                      height: '6px',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${status?.progress_percentage ?? 0}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #06b6d4, #8b5cf6)',
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Metadata Details */}
              <div
                style={{
                  display: 'flex',
                  gap: '24px',
                  marginTop: '14px',
                  fontSize: '12px',
                  color: 'var(--text-dim)',
                }}
              >
                <div>
                  Files Detected: <strong style={{ color: 'var(--text-muted)' }}>{repo.file_count || 0}</strong>
                </div>
                <div>
                  Last Indexed:{' '}
                  <strong style={{ color: 'var(--text-muted)' }}>
                    {repo.indexed_at ? new Date(repo.indexed_at).toLocaleString() : 'Never'}
                  </strong>
                </div>
                {repo.commit_hash && (
                  <div>
                    Git Commit: <strong style={{ color: 'var(--text-muted)' }}>{repo.commit_hash.slice(0, 8)}</strong>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
