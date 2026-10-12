import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, NavTab } from './components/Sidebar';
import { OverviewPage } from './features/dashboard/OverviewPage';
import { RepositoriesPage } from './features/repositories/RepositoriesPage';
import { AssistantPage } from './features/assistant/AssistantPage';
import { GraphExplorerPage } from './features/graph/GraphExplorerPage';
import { EvidencePage } from './features/evidence/EvidencePage';
import { EvaluationsPage } from './features/evaluations/EvaluationsPage';
import { Repository, SystemStatus, Citation } from './types';
import { api } from './api/client';

export const App: React.FC = () => {
  const getInitialTab = (): NavTab => {
    const rawHash = window.location.hash.replace('#', '') as NavTab;
    const validTabs: NavTab[] = ['overview', 'repositories', 'assistant', 'graph', 'evidence', 'evaluations'];
    if (validTabs.includes(rawHash)) return rawHash;
    const params = new URLSearchParams(window.location.search);
    const rawParam = params.get('tab') as NavTab;
    if (validTabs.includes(rawParam)) return rawParam;
    return 'overview';
  };

  const [currentTab, setCurrentTabState] = useState<NavTab>(getInitialTab);

  const setCurrentTab = (tab: NavTab) => {
    window.location.hash = tab;
    setCurrentTabState(tab);
  };

  useEffect(() => {
    const handleHashChange = () => {
      const rawHash = window.location.hash.replace('#', '') as NavTab;
      const validTabs: NavTab[] = ['overview', 'repositories', 'assistant', 'graph', 'evidence', 'evaluations'];
      if (validTabs.includes(rawHash)) {
        setCurrentTabState(rawHash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<string>('agent_chess');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [explorerSubgraph, setExplorerSubgraph] = useState<any>(null);

  const fetchRepositories = async () => {
    try {
      const repos = await api.listRepositories();
      setRepositories(repos);
      if (repos.length > 0 && !repos.find((r) => r.id === activeRepoId)) {
        setActiveRepoId(repos[0].id);
      }
    } catch (err) {
      console.error('Failed to load repositories', err);
    }
  };

  const fetchStatus = async () => {
    try {
      const status = await api.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Failed to load system status', err);
    }
  };

  useEffect(() => {
    fetchRepositories();
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const activeRepo = repositories.find((r) => r.id === activeRepoId) || repositories[0];

  const handleOpenCitation = (citation: Citation) => {
    setActiveCitation(citation);
    setCurrentTab('evidence');
  };

  const handleViewInGraph = (subgraphOrSymbol: any) => {
    if (typeof subgraphOrSymbol === 'object') {
      setExplorerSubgraph(subgraphOrSymbol);
    }
    setCurrentTab('graph');
  };

  return (
    <div className="layout-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Navbar
        repositories={repositories}
        activeRepoId={activeRepoId}
        onSelectRepo={(id) => setActiveRepoId(id)}
        systemStatus={systemStatus}
      />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar currentTab={currentTab} onTabChange={setCurrentTab} />

        <main className="main-content">
          {currentTab === 'overview' && (
            <OverviewPage
              activeRepo={activeRepo}
              systemStatus={systemStatus}
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'repositories' && (
            <RepositoriesPage
              repositories={repositories}
              activeRepoId={activeRepoId}
              onSelectRepo={setActiveRepoId}
              onRefreshRepos={fetchRepositories}
            />
          )}

          {currentTab === 'assistant' && (
            <AssistantPage
              activeRepo={activeRepo}
              onOpenCitation={handleOpenCitation}
              onViewInGraph={handleViewInGraph}
            />
          )}

          {currentTab === 'graph' && (
            <GraphExplorerPage
              activeRepo={activeRepo}
              initialSubgraph={explorerSubgraph}
              onOpenCitation={handleOpenCitation}
            />
          )}

          {currentTab === 'evidence' && (
            <EvidencePage
              activeRepo={activeRepo}
              activeCitation={activeCitation}
              onViewInGraph={(sym) => handleViewInGraph(sym)}
            />
          )}

          {currentTab === 'evaluations' && (
            <EvaluationsPage activeRepo={activeRepo} />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
