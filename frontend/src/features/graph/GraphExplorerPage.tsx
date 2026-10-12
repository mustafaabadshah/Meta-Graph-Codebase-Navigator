import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  Node,
  Edge,
  MarkerType,
  BackgroundVariant,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from '@dagrejs/dagre';
import {
  Search,
  Sliders,
  FileCode,
  Layers,
  Code2,
  ExternalLink,
  RefreshCw,
  GitCommit,
  PhoneCall,
  PhoneIncoming,
  ArrowRight,
  Filter,
  Maximize2,
  Minimize2,
  Sparkles,
  Compass,
} from 'lucide-react';
import { Repository, GraphNode, Citation } from '../../types';
import { api } from '../../api/client';

interface GraphExplorerPageProps {
  activeRepo: Repository | undefined;
  initialSubgraph?: any;
  onOpenCitation: (citation: Citation) => void;
}

const NODE_WIDTH = 240;
const NODE_HEIGHT = 100;

// Hierarchical Dagre Layout Engine
const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: isHorizontal ? 70 : 80,
    ranksep: isHorizontal ? 140 : 120,
    marginx: 50,
    marginy: 50,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const targetPosition = isHorizontal ? Position.Left : Position.Top;
  const sourcePosition = isHorizontal ? Position.Right : Position.Bottom;

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id) || { x: 0, y: 0 };
    return {
      ...node,
      targetPosition,
      sourcePosition,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// Custom Node Card Component with React Flow Handles
const CustomNodeCard = ({ data, targetPosition = Position.Top, sourcePosition = Position.Bottom }: any) => {
  const typeStyles: Record<string, { bg: string; border: string; text: string; icon: any }> = {
    File: { bg: 'rgba(6, 182, 212, 0.12)', border: '#06b6d4', text: '#38bdf8', icon: FileCode },
    Class: { bg: 'rgba(139, 92, 246, 0.12)', border: '#8b5cf6', text: '#a78bfa', icon: Layers },
    Function: { bg: 'rgba(16, 185, 129, 0.12)', border: '#10b981', text: '#34d399', icon: Code2 },
    Module: { bg: 'rgba(245, 158, 11, 0.12)', border: '#f59e0b', text: '#fbbf24', icon: GitCommit },
    ExternalSymbol: { bg: 'rgba(244, 63, 94, 0.12)', border: '#f43f5e', text: '#fb7185', icon: ExternalLink },
    Repository: { bg: 'rgba(99, 102, 241, 0.12)', border: '#6366f1', text: '#818cf8', icon: Compass },
  };

  const style = typeStyles[data.type] || typeStyles.Function;
  const Icon = style.icon;

  return (
    <div
      style={{
        background: '#0d131f',
        border: `1.5px solid ${data.isSelected ? '#38bdf8' : style.border}`,
        borderRadius: '10px',
        padding: '12px 14px',
        width: `${NODE_WIDTH}px`,
        boxShadow: data.isSelected
          ? `0 0 20px rgba(56, 189, 248, 0.4), 0 8px 24px rgba(0,0,0,0.6)`
          : '0 4px 16px rgba(0,0,0,0.5)',
        color: '#fff',
        position: 'relative',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
    >
      {/* Input Handle */}
      <Handle
        id="target"
        type="target"
        position={targetPosition}
        style={{
          background: style.border,
          border: '2px solid #0d131f',
          width: 10,
          height: 10,
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Icon size={13} color={style.text} />
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              textTransform: 'uppercase',
              color: style.text,
              background: style.bg,
              padding: '2px 7px',
              borderRadius: '4px',
              letterSpacing: '0.04em',
            }}
          >
            {data.type}
          </span>
        </div>
        {data.start_line && (
          <span
            style={{
              fontSize: '10px',
              color: 'var(--text-dim)',
              fontFamily: 'var(--font-mono)',
              background: 'rgba(255,255,255,0.05)',
              padding: '1px 5px',
              borderRadius: '3px',
            }}
          >
            L{data.start_line}{data.end_line ? `-${data.end_line}` : ''}
          </span>
        )}
      </div>

      <div
        style={{
          fontSize: '13px',
          fontWeight: 600,
          wordBreak: 'break-word',
          lineHeight: 1.35,
          color: '#f8fafc',
          maxHeight: '38px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
        title={data.name}
      >
        {data.name}
      </div>

      {data.rel_path && (
        <div
          style={{
            fontSize: '10px',
            color: 'var(--text-muted)',
            marginTop: '6px',
            fontFamily: 'var(--font-mono)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
          title={data.rel_path}
        >
          {data.rel_path}
        </div>
      )}

      {/* Output Handle */}
      <Handle
        id="source"
        type="source"
        position={sourcePosition}
        style={{
          background: style.border,
          border: '2px solid #0d131f',
          width: 10,
          height: 10,
        }}
      />
    </div>
  );
};

const GraphCanvasInner: React.FC<GraphExplorerPageProps> = ({
  activeRepo,
  initialSubgraph,
  onOpenCitation,
}) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeRelationships, setNodeRelationships] = useState<any>(null);
  const [depth, setDepth] = useState(2);
  const [nodeLimit, setNodeLimit] = useState(80);
  const [viewMode, setViewMode] = useState<'architecture' | 'modules' | 'hierarchy' | 'all'>('architecture');
  const [focusedSymbolId, setFocusedSymbolId] = useState<string | null>(null);
  const [layoutDirection, setLayoutDirection] = useState<'TB' | 'LR'>('TB');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rawGraphData, setRawGraphData] = useState<{ nodes: GraphNode[]; edges: any[] } | null>(null);

  // Filters
  const [entityFilter, setEntityFilter] = useState<Record<string, boolean>>({
    File: true,
    Class: true,
    Function: true,
    Module: true,
    ExternalSymbol: true,
  });

  const [edgeFilter, setEdgeFilter] = useState<Record<string, boolean>>({
    CALLS: true,
    IMPORTS: true,
    INHERITS: true,
    CONTAINS: true,
    DEFINES: true,
    HANDLES: true,
    RAISES: true,
  });

  const nodeTypes = useMemo(() => ({ custom: CustomNodeCard }), []);

  // Compute Layout with Dagre
  const applyLayout = useCallback(
    (rawNodes: GraphNode[], rawEdges: any[], direction: 'TB' | 'LR', selectedId?: string) => {
      // Filter nodes based on selected entity types
      const filteredRawNodes = rawNodes.filter((n) => entityFilter[n.type] !== false);
      const validNodeIds = new Set(filteredRawNodes.map((n) => n.id));

      // Filter edges based on visible nodes and selected edge types
      const filteredRawEdges = rawEdges.filter(
        (e) =>
          validNodeIds.has(e.source) &&
          validNodeIds.has(e.target) &&
          edgeFilter[e.type] !== false
      );

      const flowNodes: Node[] = filteredRawNodes.map((n) => ({
        id: n.id,
        type: 'custom',
        position: { x: 0, y: 0 },
        data: { ...n, isSelected: selectedId === n.id },
      }));

      const flowEdges: Edge[] = filteredRawEdges.map((e: any, i: number) => {
        const isCall = e.type === 'CALLS';
        const isImport = e.type === 'IMPORTS';
        const isInherits = e.type === 'INHERITS';
        const isDefines = e.type === 'DEFINES';
        const isContains = e.type === 'CONTAINS';
        const isHandles = e.type === 'HANDLES';
        const isRaises = e.type === 'RAISES';

        const color = isCall
          ? '#f43f5e'
          : isImport
          ? '#06b6d4'
          : isInherits
          ? '#8b5cf6'
          : isDefines
          ? '#10b981'
          : isHandles || isRaises
          ? '#f59e0b'
          : '#64748b';

        return {
          id: `e-${e.source}-${e.target}-${i}`,
          source: e.source,
          target: e.target,
          sourceHandle: 'source',
          targetHandle: 'target',
          type: 'smoothstep',
          animated: isCall,
          label: e.type,
          style: {
            stroke: color,
            strokeWidth: isCall ? 2 : 1.5,
          },
          labelStyle: { fill: color, fontSize: 9, fontWeight: 700 },
          labelBgStyle: { fill: '#0a0d14', fillOpacity: 0.85, rx: 4, ry: 4 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: color,
            width: 14,
            height: 14,
          },
        };
      });

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        flowNodes,
        flowEdges,
        direction
      );

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);

      setTimeout(() => {
        fitView({ padding: 0.15, duration: 500 });
      }, 50);
    },
    [entityFilter, edgeFilter, fitView, setNodes, setEdges]
  );

  const loadGraph = useCallback(
    async (
      subgraphData?: any,
      focusId?: string | null,
      customViewMode?: 'architecture' | 'modules' | 'hierarchy' | 'all'
    ) => {
      if (!activeRepo) return;
      try {
        setLoading(true);
        const mode = customViewMode || viewMode;
        const targetFocus = focusId !== undefined ? focusId : focusedSymbolId;
        const data =
          subgraphData ||
          (await api.getGraph(activeRepo.id, depth, nodeLimit, mode, targetFocus || undefined));
        setRawGraphData(data);
        applyLayout(data.nodes || [], data.edges || [], layoutDirection, selectedNode?.id);
      } catch (err) {
        console.error('Failed to load graph:', err);
      } finally {
        setLoading(false);
      }
    },
    [activeRepo, depth, nodeLimit, viewMode, focusedSymbolId, layoutDirection, selectedNode?.id, applyLayout]
  );

  useEffect(() => {
    if (initialSubgraph) {
      loadGraph(initialSubgraph);
    } else {
      loadGraph();
    }
  }, [activeRepo?.id, depth, nodeLimit, viewMode, focusedSymbolId, initialSubgraph]);

  // Re-layout when filters or direction changes
  useEffect(() => {
    if (rawGraphData) {
      applyLayout(rawGraphData.nodes || [], rawGraphData.edges || [], layoutDirection, selectedNode?.id);
    }
  }, [layoutDirection, entityFilter, edgeFilter]);

  const onNodeClick = async (_: any, node: Node) => {
    const nodeData = (node.data as unknown) as GraphNode;
    setSelectedNode(nodeData);

    // Update isSelected state on nodes
    setNodes((prevNodes) =>
      prevNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          isSelected: n.id === node.id,
        },
      }))
    );

    if (activeRepo) {
      try {
        const rels = await api.getSymbolRelationships(activeRepo.id, nodeData.id);
        setNodeRelationships(rels);
      } catch {
        setNodeRelationships(null);
      }
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !activeRepo) return;
    try {
      setLoading(true);
      const matches = await api.searchSymbols(activeRepo.id, searchQuery, 15);
      setSearchResults(matches);
      if (matches.length > 0) {
        const topMatch = matches[0];
        setFocusedSymbolId(topMatch.id);
        const data = await api.getGraph(activeRepo.id, depth, nodeLimit, viewMode, topMatch.id);
        setRawGraphData(data);
        const found = data.nodes?.find((n: any) => n.id === topMatch.id) || topMatch;
        setSelectedNode(found);
        applyLayout(data.nodes || [], data.edges || [], layoutDirection, topMatch.id);
        setShowSearchResults(false);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSearchResult = async (sym: any) => {
    if (!activeRepo) return;
    setFocusedSymbolId(sym.id);
    setSearchQuery(sym.name);
    setShowSearchResults(false);
    try {
      setLoading(true);
      const data = await api.getGraph(activeRepo.id, depth, nodeLimit, viewMode, sym.id);
      setRawGraphData(data);
      const found = data.nodes?.find((n: any) => n.id === sym.id) || sym;
      setSelectedNode(found);
      applyLayout(data.nodes || [], data.edges || [], layoutDirection, sym.id);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleResetFocus = () => {
    setFocusedSymbolId(null);
    setSearchQuery('');
    setSelectedNode(null);
    setNodeRelationships(null);
    loadGraph(undefined, null);
  };

  const toggleEntityFilter = (type: string) => {
    setEntityFilter((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const toggleEdgeFilter = (type: string) => {
    setEdgeFilter((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', position: 'relative' }}>
      {/* React Flow Canvas */}
      <div style={{ flex: 1, height: '100%', position: 'relative' }}>
        {/* Canvas Primary Toolbar */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '20px',
            zIndex: 10,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(11, 15, 23, 0.92)',
            backdropFilter: 'blur(14px)',
            padding: '8px 14px',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)',
            boxShadow: '0 8px 30px rgba(0,0,0,0.6)',
          }}
        >
          {/* View Mode Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '6px' }}>
            <button
              onClick={() => { setViewMode('architecture'); setFocusedSymbolId(null); loadGraph(undefined, null, 'architecture'); }}
              style={{
                padding: '4px 9px',
                fontSize: '11px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'architecture' ? 'rgba(16, 185, 129, 0.25)' : 'transparent',
                color: viewMode === 'architecture' ? '#34d399' : 'var(--text-muted)',
              }}
              title="Class and Function Call Graph (Architecture)"
            >
              Architecture
            </button>
            <button
              onClick={() => { setViewMode('modules'); setFocusedSymbolId(null); loadGraph(undefined, null, 'modules'); }}
              style={{
                padding: '4px 9px',
                fontSize: '11px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'modules' ? 'rgba(245, 158, 11, 0.25)' : 'transparent',
                color: viewMode === 'modules' ? '#fbbf24' : 'var(--text-muted)',
              }}
              title="Module and Package Dependencies"
            >
              Modules
            </button>
            <button
              onClick={() => { setViewMode('hierarchy'); setFocusedSymbolId(null); loadGraph(undefined, null, 'hierarchy'); }}
              style={{
                padding: '4px 9px',
                fontSize: '11px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'hierarchy' ? 'rgba(139, 92, 246, 0.25)' : 'transparent',
                color: viewMode === 'hierarchy' ? '#a78bfa' : 'var(--text-muted)',
              }}
              title="File and Class Hierarchy"
            >
              Hierarchy
            </button>
            <button
              onClick={() => { setViewMode('all'); setFocusedSymbolId(null); loadGraph(undefined, null, 'all'); }}
              style={{
                padding: '4px 9px',
                fontSize: '11px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 'none',
                cursor: 'pointer',
                background: viewMode === 'all' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
                color: viewMode === 'all' ? '#38bdf8' : 'var(--text-muted)',
              }}
              title="Comprehensive Subgraph"
            >
              All
            </button>
          </div>

          <div style={{ height: '18px', width: '1px', background: 'var(--border-subtle)' }} />

          {/* Symbol Search */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative' }}>
            <Search size={14} color="var(--text-dim)" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search symbol (e.g. ChessAgent)..."
              style={{
                background: 'transparent',
                border: 'none',
                color: '#fff',
                fontSize: '12px',
                outline: 'none',
                width: '180px',
              }}
            />
            {searchQuery && (
              <button
                onClick={handleSearch}
                style={{
                  background: 'rgba(6,182,212,0.2)',
                  border: '1px solid #06b6d4',
                  color: '#06b6d4',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                Go
              </button>
            )}
          </div>

          {focusedSymbolId && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid #38bdf8',
                borderRadius: '4px',
                padding: '2px 7px',
                fontSize: '11px',
                color: '#38bdf8',
              }}
            >
              <span>Focused: {focusedSymbolId.split(':').pop()}</span>
              <button
                onClick={handleResetFocus}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#38bdf8',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  padding: 0,
                  marginLeft: '3px',
                }}
                title="Clear focus"
              >
                ✕
              </button>
            </div>
          )}

          <div style={{ height: '18px', width: '1px', background: 'var(--border-subtle)' }} />

          {/* Depth Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <Sliders size={13} color="var(--text-dim)" />
            <span style={{ color: 'var(--text-muted)' }}>Depth:</span>
            <input
              type="range"
              min={1}
              max={4}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              style={{ width: '50px', accentColor: '#06b6d4' }}
            />
            <span style={{ fontWeight: 600, color: '#06b6d4' }}>{depth}</span>
          </div>

          {/* Node Limit */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Limit:</span>
            <select
              value={nodeLimit}
              onChange={(e) => setNodeLimit(Number(e.target.value))}
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid var(--border-subtle)',
                color: '#fff',
                fontSize: '11px',
                borderRadius: '4px',
                padding: '2px 4px',
                cursor: 'pointer',
              }}
            >
              <option value={40} style={{ background: '#0d131f' }}>40</option>
              <option value={80} style={{ background: '#0d131f' }}>80</option>
              <option value={120} style={{ background: '#0d131f' }}>120</option>
              <option value={180} style={{ background: '#0d131f' }}>180</option>
            </select>
          </div>

          <div style={{ height: '18px', width: '1px', background: 'var(--border-subtle)' }} />

          {/* Direction Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              className={`btn-secondary ${layoutDirection === 'TB' ? 'active' : ''}`}
              onClick={() => setLayoutDirection('TB')}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                background: layoutDirection === 'TB' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                borderColor: layoutDirection === 'TB' ? '#06b6d4' : 'var(--border-subtle)',
                color: layoutDirection === 'TB' ? '#38bdf8' : 'var(--text-muted)',
              }}
              title="Top to Bottom Hierarchical Layout"
            >
              Top-Down
            </button>
            <button
              className={`btn-secondary ${layoutDirection === 'LR' ? 'active' : ''}`}
              onClick={() => setLayoutDirection('LR')}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                background: layoutDirection === 'LR' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                borderColor: layoutDirection === 'LR' ? '#06b6d4' : 'var(--border-subtle)',
                color: layoutDirection === 'LR' ? '#38bdf8' : 'var(--text-muted)',
              }}
              title="Left to Right Pipeline Layout"
            >
              Left-Right
            </button>
          </div>

          <div style={{ height: '18px', width: '1px', background: 'var(--border-subtle)' }} />

          {/* Reset / Reload Button */}
          <button
            className="btn-secondary"
            onClick={() => loadGraph()}
            style={{ padding: '4px 10px', fontSize: '12px' }}
            title="Refresh Graph"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            <span>Reload</span>
          </button>

          {/* Fit View Button */}
          <button
            className="btn-secondary"
            onClick={() => fitView({ padding: 0.15, duration: 400 })}
            style={{ padding: '4px 10px', fontSize: '12px' }}
            title="Fit Graph to View"
          >
            <Maximize2 size={12} />
            <span>Fit</span>
          </button>
        </div>

        {/* Secondary Filter Bar */}
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            zIndex: 10,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(11, 15, 23, 0.85)',
            backdropFilter: 'blur(10px)',
            padding: '8px 14px',
            borderRadius: '8px',
            border: '1px solid var(--border-subtle)',
            fontSize: '11px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-dim)', fontWeight: 600 }}>
            <Filter size={12} />
            <span>Filter Entities:</span>
          </div>

          {[
            { key: 'File', label: 'File', color: '#06b6d4' },
            { key: 'Class', label: 'Class', color: '#8b5cf6' },
            { key: 'Function', label: 'Function', color: '#10b981' },
            { key: 'Module', label: 'Module', color: '#f59e0b' },
            { key: 'ExternalSymbol', label: 'External', color: '#f43f5e' },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => toggleEntityFilter(item.key)}
              style={{
                background: entityFilter[item.key] ? `${item.color}20` : 'transparent',
                border: `1px solid ${entityFilter[item.key] ? item.color : '#334155'}`,
                color: entityFilter[item.key] ? item.color : '#64748b',
                padding: '3px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 600,
                transition: 'all 0.15s ease',
              }}
            >
              {item.label}
            </button>
          ))}

          <div style={{ height: '14px', width: '1px', background: 'var(--border-subtle)', margin: '0 4px' }} />

          <div style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Edges:</div>

          {[
            { key: 'CALLS', label: 'Calls', color: '#f43f5e' },
            { key: 'IMPORTS', label: 'Imports', color: '#06b6d4' },
            { key: 'INHERITS', label: 'Inherits', color: '#8b5cf6' },
            { key: 'DEFINES', label: 'Defines', color: '#10b981' },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => toggleEdgeFilter(item.key)}
              style={{
                background: edgeFilter[item.key] ? `${item.color}20` : 'transparent',
                border: `1px solid ${edgeFilter[item.key] ? item.color : '#334155'}`,
                color: edgeFilter[item.key] ? item.color : '#64748b',
                padding: '3px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 600,
                transition: 'all 0.15s ease',
              }}
            >
              {item.label}
            </button>
          ))}

          <span style={{ color: 'var(--text-dim)', marginLeft: '6px' }}>
            ({nodes.length} nodes, {edges.length} edges)
          </span>
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.1}
          maxZoom={2.0}
          style={{ background: '#080b12' }}
        >
          <Background color="#161f30" gap={24} size={1} variant={BackgroundVariant.Dots} />
          <Controls style={{ background: '#121826', border: '1px solid var(--border-subtle)', fill: '#fff' }} />
          <MiniMap
            style={{ background: '#0b0f17', border: '1px solid var(--border-subtle)' }}
            nodeColor={(n: any) => {
              if (n.data?.type === 'File') return '#06b6d4';
              if (n.data?.type === 'Class') return '#8b5cf6';
              if (n.data?.type === 'Function') return '#10b981';
              if (n.data?.type === 'Module') return '#f59e0b';
              if (n.data?.type === 'ExternalSymbol') return '#f43f5e';
              return '#6366f1';
            }}
          />
        </ReactFlow>
      </div>

      {/* Node Details Inspector Sidebar */}
      {selectedNode && (
        <div
          style={{
            width: '380px',
            height: '100%',
            background: 'rgba(11, 15, 23, 0.95)',
            borderLeft: '1px solid var(--border-subtle)',
            backdropFilter: 'blur(12px)',
            display: 'flex',
            flexDirection: 'column',
            padding: '24px',
            overflowY: 'auto',
            zIndex: 20,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <span className="badge badge-cyan">{selectedNode.type}</span>
            <button
              onClick={() => setSelectedNode(null)}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '16px' }}
            >
              ✕
            </button>
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0, wordBreak: 'break-word', color: '#f8fafc' }}>
            {selectedNode.name}
          </h3>

          {selectedNode.qualified_name && (
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: '#38bdf8',
                marginTop: '6px',
                wordBreak: 'break-all',
              }}
            >
              {selectedNode.qualified_name}
            </div>
          )}

          {selectedNode.rel_path && (
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
                color: 'var(--text-muted)',
                marginTop: '10px',
                background: 'rgba(255,255,255,0.03)',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              📄 {selectedNode.rel_path} {selectedNode.start_line ? `(L${selectedNode.start_line}-${selectedNode.end_line})` : ''}
            </div>
          )}

          {/* Docstring */}
          {selectedNode.docstring && (
            <div style={{ marginTop: '16px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '4px' }}>
                Docstring:
              </div>
              <div
                style={{
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                  background: 'rgba(0,0,0,0.3)',
                  padding: '10px',
                  borderRadius: '6px',
                  fontStyle: 'italic',
                  lineHeight: 1.5,
                }}
              >
                {selectedNode.docstring}
              </div>
            </div>
          )}

          {/* Open in Evidence Viewer Action */}
          {selectedNode.rel_path && (
            <button
              className="btn-primary"
              onClick={() =>
                onOpenCitation({
                  repository: activeRepo?.id || 'agent_chess',
                  file: selectedNode.rel_path!,
                  symbol: selectedNode.qualified_name || selectedNode.name,
                  start_line: selectedNode.start_line || 1,
                  end_line: selectedNode.end_line || selectedNode.start_line || 50,
                })
              }
              style={{ marginTop: '20px', width: '100%', justifyContent: 'center', padding: '10px' }}
            >
              <FileCode size={15} />
              <span>Inspect Source in Evidence Viewer</span>
            </button>
          )}

          {/* Incoming Callers */}
          {nodeRelationships?.callers?.length > 0 && (
            <div style={{ marginTop: '24px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <PhoneIncoming size={14} color="#10b981" />
                Callers ({nodeRelationships.callers.length}):
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {nodeRelationships.callers.slice(0, 8).map((caller: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      fontSize: '11px',
                      background: 'rgba(255,255,255,0.02)',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ fontWeight: 600, color: '#34d399' }}>{caller.qualified_name || caller.name}</div>
                    <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      Call line {caller.call_line}: {caller.call_expr}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outgoing Callees */}
          {nodeRelationships?.callees?.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <PhoneCall size={14} color="#f43f5e" />
                Callees ({nodeRelationships.callees.length}):
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {nodeRelationships.callees.slice(0, 8).map((callee: any, i: number) => (
                  <div
                    key={i}
                    style={{
                      fontSize: '11px',
                      background: 'rgba(255,255,255,0.02)',
                      padding: '8px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ fontWeight: 600, color: '#fb7185' }}>{callee.qualified_name || callee.name}</div>
                    <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                      Call line {callee.call_line}: {callee.call_expr}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const GraphExplorerPage: React.FC<GraphExplorerPageProps> = (props) => {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
};
