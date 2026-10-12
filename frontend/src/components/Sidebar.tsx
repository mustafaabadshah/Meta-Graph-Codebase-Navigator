import React from 'react';
import {
  LayoutDashboard,
  FolderGit2,
  Bot,
  Network,
  FileCode2,
  Award,
} from 'lucide-react';

export type NavTab = 'overview' | 'repositories' | 'assistant' | 'graph' | 'evidence' | 'evaluations';

interface SidebarProps {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange }) => {
  const tabs = [
    { id: 'overview' as NavTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'repositories' as NavTab, label: 'Repositories', icon: FolderGit2 },
    { id: 'assistant' as NavTab, label: 'AI Assistant', icon: Bot },
    { id: 'graph' as NavTab, label: 'Graph Explorer', icon: Network },
    { id: 'evidence' as NavTab, label: 'Evidence Viewer', icon: FileCode2 },
    { id: 'evaluations' as NavTab, label: 'Evaluations', icon: Award },
  ];

  return (
    <aside
      style={{
        width: '240px',
        borderRight: '1px solid var(--border-subtle)',
        background: 'rgba(11, 15, 23, 0.7)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '20px 14px',
      }}
    >
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div
          style={{
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.8px',
            color: 'var(--text-dim)',
            padding: '6px 12px 10px',
            fontWeight: 700,
          }}
        >
          Navigation
        </div>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentTab === tab.id;
          return (
            <button
              key={tab.id}
              className={`nav-tab ${isActive ? 'active' : ''}`}
              onClick={() => onTabChange(tab.id)}
              style={{
                width: '100%',
                background: isActive ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
                textAlign: 'left',
              }}
            >
              <Icon size={17} color={isActive ? '#38bdf8' : '#94a3b8'} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div
        className="glass-panel"
        style={{
          padding: '14px',
          fontSize: '12px',
          color: 'var(--text-dim)',
          lineHeight: 1.5,
        }}
      >
        <div style={{ fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
          AST Graph Engine
        </div>
        <div>Bounded Cypher Multi-Hop Traversal & LLM Grounding</div>
      </div>
    </aside>
  );
};
