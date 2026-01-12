import { useMemo, useEffect, useState } from 'react';
import { Network, GitBranch, Layers, Play, Pause, CheckCircle2, MessageSquare, X } from 'lucide-react';
import type { Task } from '../../types/task';
import type { Agent } from '../../types';
import { useTaskStore } from '../../stores/taskStore';
import { useWebSocketStore } from '../../stores/websocketStore';

interface TaskGraphPanelProps {
  task?: Task;
  allTasks: Task[];
  agents: Agent[];
  onSendMessage?: (taskId: string, message: string) => void;
  onNodeSelect?: (node: TaskGraphNodeData | null) => void;
  selectedNodeId?: string | null;
}

export type { TaskGraphNodeData };

export function TaskGraphPanel({ task, onSendMessage }: TaskGraphPanelProps) {
  const { getTaskGraph, getTaskChatMessages, agentLogs } = useTaskStore();
  const { requestTaskGraph } = useWebSocketStore();
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messageInput, setMessageInput] = useState('');
  const [selectedNode, setSelectedNode] = useState<TaskGraphNodeData | null>(null);

  // Request task graph when task changes
  useEffect(() => {
    if (task?.id) {
      requestTaskGraph(task.id);
    }
  }, [task?.id, requestTaskGraph]);

  // Get task graph from store
  const graphData = task?.id ? getTaskGraph(task.id) : null;
  
  // Get chat messages
  const chatMessages = task?.id ? getTaskChatMessages(task.id) : [];

  // Debug: log graph data
  useEffect(() => {
    if (task?.id) {
      console.log('[TaskGraphPanel] Task ID:', task.id);
      console.log('[TaskGraphPanel] Graph data:', graphData);
    }
  }, [task?.id, graphData]);

  // Parse graph data and create nodes/edges with hierarchical layout
  const graphNodes = useMemo((): TaskGraphNodeData[] => {
    if (!graphData || !graphData.nodes) return [];

    const nodeMap: Record<string, any> = graphData.nodes || {};
    const nodeEntries = Object.entries(nodeMap);

    // Calculate hierarchical levels based on dependencies
    const levels: Map<string, number> = new Map();
    const nodesByLevel: Map<number, string[]> = new Map();

    // Helper function to calculate node level (depth in dependency tree)
    function getNodeLevel(nodeId: string, visited = new Set<string>()): number {
      if (levels.has(nodeId)) return levels.get(nodeId)!;
      if (visited.has(nodeId)) return 0; // Circular dependency

      visited.add(nodeId);
      const nodeData = nodeMap[nodeId];
      const deps = nodeData?.dependencies || [];

      if (deps.length === 0) {
        levels.set(nodeId, 0);
        return 0;
      }

      const maxDepLevel = Math.max(...deps.map((dep: string) => getNodeLevel(dep, new Set(visited))));
      const level = maxDepLevel + 1;
      levels.set(nodeId, level);
      return level;
    }

    // Calculate levels for all nodes
    nodeEntries.forEach(([nodeId]) => {
      const level = getNodeLevel(nodeId);
      if (!nodesByLevel.has(level)) {
        nodesByLevel.set(level, []);
      }
      nodesByLevel.get(level)!.push(nodeId);
    });

    // Layout nodes hierarchically
    const nodes: TaskGraphNodeData[] = [];
    const maxLevel = Math.max(...Array.from(levels.values()));
    const verticalSpacing = 120;
    const horizontalSpacing = 240;
    const startY = 80;

    for (let level = 0; level <= maxLevel; level++) {
      const nodesInLevel = nodesByLevel.get(level) || [];
      const levelWidth = nodesInLevel.length * horizontalSpacing;
      const startX = Math.max(100, (800 - levelWidth) / 2); // Center nodes

      nodesInLevel.forEach((nodeId, index) => {
        const nodeData = nodeMap[nodeId];
        nodes.push({
          id: nodeId,
          label: nodeData.name || nodeData.label || nodeId,
          status: mapStatus(nodeData.status),
          x: startX + index * horizontalSpacing,
          y: startY + level * verticalSpacing,
          dependencies: nodeData.dependencies || [],
          complexity: nodeData.complexity || nodeData.metadata?.complexity || 3,
        });
      });
    }

    return nodes;
  }, [graphData]);

  const graphEdges = useMemo(() => {
    const edges: { from: string; to: string; animated?: boolean }[] = [];
    graphNodes.forEach(node => {
      node.dependencies?.forEach(dep => {
        edges.push({
          from: dep,
          to: node.id,
          animated: node.status === 'in_progress',
        });
      });
    });
    return edges;
  }, [graphNodes]);

  // Helper function to map backend status to frontend status
  function mapStatus(status: string): 'pending' | 'in_progress' | 'completed' | 'failed' {
    if (status === 'completed' || status === 'COMPLETED') return 'completed';
    if (status === 'running' || status === 'RUNNING' || status === 'in_progress') return 'in_progress';
    if (status === 'failed' || status === 'FAILED') return 'failed';
    return 'pending';
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-400/10 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase flex items-center gap-2">
            <Network className="w-4 h-4" />
            Task Decomposition Graph
          </h2>
          {task && (
            <p className="text-xs text-gray-500 mt-0.5">{task.title}</p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {task && (
            <button
              onClick={() => setIsChatOpen(!isChatOpen)}
              className="p-1.5 hover:bg-cyan-500/10 rounded border border-transparent hover:border-cyan-400/30 transition-colors relative"
              title="Task Chat"
            >
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              {chatMessages.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
                  {chatMessages.length}
                </span>
              )}
            </button>
          )}
          <button className="p-1.5 hover:bg-cyan-500/10 rounded border border-transparent hover:border-cyan-400/30 transition-colors">
            <GitBranch className="w-4 h-4 text-cyan-400" />
          </button>
          <button className="p-1.5 hover:bg-cyan-500/10 rounded border border-transparent hover:border-cyan-400/30 transition-colors">
            <Layers className="w-4 h-4 text-cyan-400" />
          </button>
        </div>
      </div>

      {/* Graph Visualization */}
      <div className="flex-1 relative overflow-auto bg-[#0a0e1a]/50">
        {task ? (
          <div className="relative min-h-[600px] min-w-[800px] p-8">
            {/* SVG Canvas - Behind nodes */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
              <defs>
                {/* Glow filter */}
                <filter id="glow">
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>

                {/* Arrow marker */}
                <marker
                  id="arrowhead"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L0,6 L9,3 z" fill="rgba(34, 211, 238, 0.8)" />
                </marker>

                <marker
                  id="arrowhead-active"
                  markerWidth="10"
                  markerHeight="10"
                  refX="8"
                  refY="3"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L0,6 L9,3 z" fill="#22d3ee" />
                </marker>

                {/* Gradient for edges */}
                <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="rgba(34, 211, 238, 0.6)" />
                  <stop offset="100%" stopColor="rgba(139, 92, 246, 0.6)" />
                </linearGradient>

                {/* Animated gradient for active edges */}
                <linearGradient id="edgeGradientActive" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="rgba(34, 211, 238, 1)">
                    <animate attributeName="stop-color" values="rgba(34, 211, 238, 1); rgba(236, 72, 153, 1); rgba(34, 211, 238, 1)" dur="2s" repeatCount="indefinite" />
                  </stop>
                  <stop offset="100%" stopColor="rgba(139, 92, 246, 1)">
                    <animate attributeName="stop-color" values="rgba(139, 92, 246, 1); rgba(34, 211, 238, 1); rgba(139, 92, 246, 1)" dur="2s" repeatCount="indefinite" />
                  </stop>
                </linearGradient>
              </defs>

              {/* Edges */}
              <g className="edges">
                {graphEdges.map((edge, idx) => {
                  const fromNode = graphNodes.find(n => n.id === edge.from);
                  const toNode = graphNodes.find(n => n.id === edge.to);
                  if (!fromNode || !toNode) return null;

                  // Node centers
                  const startX = fromNode.x + 120;
                  const startY = fromNode.y + 35;
                  const endX = toNode.x + 120;
                  const endY = toNode.y + 5;

                  // Smooth cubic bezier curve
                  const controlY1 = startY + (endY - startY) * 0.5;
                  const controlY2 = startY + (endY - startY) * 0.5;
                  const curvePath = `M ${startX},${startY} C ${startX},${controlY1} ${endX},${controlY2} ${endX},${endY}`;

                  return (
                    <g key={idx}>
                      {/* Shadow/glow path */}
                      <path
                        d={curvePath}
                        stroke={edge.animated ? 'rgba(34, 211, 238, 0.3)' : 'rgba(34, 211, 238, 0.2)'}
                        strokeWidth="6"
                        fill="none"
                        filter="url(#glow)"
                        className="transition-all"
                      />
                      {/* Main path */}
                      <path
                        d={curvePath}
                        stroke={edge.animated ? 'url(#edgeGradientActive)' : 'url(#edgeGradient)'}
                        strokeWidth="2"
                        fill="none"
                        className="transition-all"
                        strokeLinecap="round"
                        markerEnd={edge.animated ? 'url(#arrowhead-active)' : 'url(#arrowhead)'}
                      />
                      {/* Animated circle for active edges */}
                      {edge.animated && (
                        <circle r="4" fill="#22d3ee" filter="url(#glow)">
                          <animateMotion
                            dur="2s"
                            repeatCount="indefinite"
                            path={curvePath}
                          />
                        </circle>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* Nodes - Above SVG */}
            <div className="relative w-full h-full" style={{ zIndex: 2 }}>
              {graphNodes.length > 0 ? (
                graphNodes.map(node => (
                  <TaskGraphNode
                    key={node.id}
                    node={node}
                    onClick={() => setSelectedNode(node)}
                    isSelected={selectedNode?.id === node.id}
                  />
                ))
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-600">
                  <Network className="w-12 h-12 mb-3 opacity-20" />
                  <p className="text-sm">No graph data available</p>
                  <p className="text-xs text-gray-700 mt-1">Task graph will appear when decomposition is available</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <Network className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-sm">Select a task to view decomposition graph</p>
            <p className="text-xs text-gray-700 mt-1">Task graphs visualize subtask dependencies and execution flow</p>
          </div>
        )}
      </div>

      {/* Footer with Legend */}
      {task && (
        <div className="px-4 py-2 border-t border-cyan-400/10 flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <LegendItem color="bg-emerald-400" label="Completed" />
            <LegendItem color="bg-cyan-400 animate-pulse" label="In Progress" />
            <LegendItem color="bg-amber-400/50" label="Pending" />
          </div>
          <div className="text-gray-500">
            {graphNodes.length} nodes • {graphEdges.length} edges
          </div>
        </div>
      )}

      {/* Step Detail Panel */}
      {selectedNode && task && (
        <div className="absolute top-16 right-4 w-96 max-h-[calc(100%-5rem)] bg-gradient-to-br from-[#1a1f2e]/95 to-[#0d1117]/95 border border-cyan-400/20 rounded-xl flex flex-col shadow-2xl backdrop-blur-xl overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-cyan-400/10 flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">Step Details</h3>
              <p className="text-xs text-gray-400 truncate mt-0.5">{selectedNode.label}</p>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="ml-2 p-1 hover:bg-red-500/10 rounded text-gray-400 hover:text-red-400 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Status & Metrics */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</span>
                <span className={`text-xs font-bold px-2 py-1 rounded ${
                  selectedNode.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' :
                  selectedNode.status === 'in_progress' ? 'bg-cyan-500/20 text-cyan-300' :
                  selectedNode.status === 'failed' ? 'bg-red-500/20 text-red-300' :
                  'bg-amber-500/20 text-amber-300'
                }`}>
                  {selectedNode.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px] text-gray-400">
                  <span>Complexity</span>
                  <span className="font-mono tabular-nums">{selectedNode.complexity}/10</span>
                </div>
                <div className="flex gap-1">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div
                      key={i}
                      className={`h-1.5 flex-1 rounded-full transition-all ${
                        i < selectedNode.complexity
                          ? 'bg-cyan-400 opacity-80'
                          : 'bg-gray-700/50 opacity-40'
                      }`}
                    />
                  ))}
                </div>
              </div>

              {selectedNode.dependencies && selectedNode.dependencies.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Dependencies</span>
                  <div className="mt-1 space-y-1">
                    {selectedNode.dependencies.map((dep) => (
                      <div key={dep} className="text-xs text-gray-500 bg-gray-800/50 px-2 py-1 rounded border border-gray-700/50">
                        {graphNodes.find(n => n.id === dep)?.label || dep}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Context Information */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Context</h4>
              <div className="bg-black/30 border border-cyan-400/10 rounded-lg p-3">
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Step ID:</span>
                    <span className="text-gray-300 font-mono">{selectedNode.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Position:</span>
                    <span className="text-gray-300 font-mono">({selectedNode.x}, {selectedNode.y})</span>
                  </div>
                  {graphData?.nodes?.[selectedNode.id]?.metadata && (
                    <div className="pt-2 border-t border-gray-700/50">
                      <span className="text-gray-500 block mb-1">Metadata:</span>
                      <pre className="text-[10px] text-gray-400 bg-black/50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(graphData.nodes[selectedNode.id].metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Agent Logs for this step */}
            {agentLogs.filter(log => log.step === selectedNode.id || log.context?.stepId === selectedNode.id).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Agent Logs</h4>
                <div className="space-y-2">
                  {agentLogs
                    .filter(log => log.step === selectedNode.id || log.context?.stepId === selectedNode.id)
                    .slice(-5)
                    .map((log, idx) => (
                      <div key={idx} className="bg-black/30 border border-gray-700/50 rounded-lg p-2">
                        <div className="flex items-start justify-between mb-1">
                          <span className="text-[10px] font-semibold text-cyan-400">{log.type}</span>
                          <span className="text-[10px] text-gray-500">
                            {new Date(log.timestamp).toLocaleTimeString('en-US', {
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit'
                            })}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 line-clamp-3">{log.message}</p>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Tool Executions */}
            {graphData?.nodes?.[selectedNode.id]?.tools && graphData.nodes[selectedNode.id].tools.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Tool Executions</h4>
                <div className="space-y-2">
                  {graphData.nodes[selectedNode.id].tools.map((tool: any, idx: number) => (
                    <div key={idx} className="bg-black/30 border border-purple-400/20 rounded-lg p-2">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                        <span className="text-xs font-semibold text-purple-300">{tool.name || 'Tool'}</span>
                      </div>
                      {tool.input && (
                        <pre className="text-[10px] text-gray-500 mt-1 line-clamp-2">
                          {JSON.stringify(tool.input, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Reasoning */}
            {graphData?.nodes?.[selectedNode.id]?.reasoning && (
              <div>
                <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Reasoning</h4>
                <div className="bg-black/30 border border-amber-400/10 rounded-lg p-3">
                  <p className="text-xs text-gray-400 whitespace-pre-wrap">
                    {graphData.nodes[selectedNode.id].reasoning}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat Panel */}
      {isChatOpen && task && (
        <div className="absolute bottom-0 right-0 w-96 h-96 bg-[#1a1f2e] border-l border-t border-cyan-400/20 rounded-tl-xl flex flex-col shadow-2xl">
          {/* Chat Header */}
          <div className="px-4 py-2 border-b border-cyan-400/10 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-cyan-300">Task Chat</h3>
              <p className="text-xs text-gray-500">{task.title}</p>
            </div>
            <button
              onClick={() => setIsChatOpen(false)}
              className="p-1 hover:bg-red-500/10 rounded text-gray-400 hover:text-red-400 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {chatMessages.length === 0 ? (
              <div className="text-center py-8 text-gray-600">
                <MessageSquare className="w-8 h-8 mb-2 opacity-20 mx-auto" />
                <p className="text-xs">No messages yet</p>
              </div>
            ) : (
              chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 ${
                      msg.role === 'user'
                        ? 'bg-cyan-600 text-white'
                        : 'bg-gray-800 text-gray-200'
                    }`}
                  >
                    {msg.role === 'agent' && msg.agentName && (
                      <p className="text-[10px] text-gray-400 mb-1">{msg.agentName}</p>
                    )}
                    <p className="text-xs whitespace-pre-wrap break-words">{msg.message}</p>
                    <p className="text-[10px] opacity-60 mt-1">
                      {new Date(msg.timestamp).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-cyan-400/10">
            <div className="flex gap-2">
              <textarea
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (messageInput.trim() && onSendMessage && task) {
                      onSendMessage(task.id, messageInput.trim());
                      setMessageInput('');
                    }
                  }
                }}
                placeholder="Type your message..."
                className="flex-1 px-2 py-1.5 bg-gray-800 text-white text-xs rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500 border border-gray-700"
                rows={2}
              />
              <button
                onClick={() => {
                  if (messageInput.trim() && onSendMessage && task) {
                    onSendMessage(task.id, messageInput.trim());
                    setMessageInput('');
                  }
                }}
                disabled={!messageInput.trim()}
                className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors self-end"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            <p className="text-[10px] text-gray-500 mt-1">Press Enter to send</p>
          </div>
        </div>
      )}
    </div>
  );
}

interface TaskGraphNodeData {
  id: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  x: number;
  y: number;
  dependencies?: string[];
  complexity: number;
}

function TaskGraphNode({ node, onClick, isSelected }: {
  node: TaskGraphNodeData;
  onClick: () => void;
  isSelected: boolean;
}) {
  const statusConfig = {
    pending: {
      border: 'border-amber-400/60',
      bg: 'bg-gradient-to-br from-amber-500/20 to-amber-600/10',
      text: 'text-amber-300',
      glow: 'shadow-lg shadow-amber-500/20',
      icon: 'text-amber-400',
      dot: 'bg-amber-400',
    },
    in_progress: {
      border: 'border-cyan-400',
      bg: 'bg-gradient-to-br from-cyan-500/30 to-blue-600/20',
      text: 'text-cyan-200',
      glow: 'shadow-xl shadow-cyan-500/40',
      icon: 'text-cyan-300',
      dot: 'bg-cyan-400 animate-pulse',
    },
    completed: {
      border: 'border-emerald-400/60',
      bg: 'bg-gradient-to-br from-emerald-500/20 to-green-600/10',
      text: 'text-emerald-300',
      glow: 'shadow-lg shadow-emerald-500/20',
      icon: 'text-emerald-400',
      dot: 'bg-emerald-400',
    },
    failed: {
      border: 'border-red-400/60',
      bg: 'bg-gradient-to-br from-red-500/20 to-red-600/10',
      text: 'text-red-300',
      glow: 'shadow-lg shadow-red-500/20',
      icon: 'text-red-400',
      dot: 'bg-red-400',
    },
  }[node.status];

  const StatusIcon = {
    pending: Pause,
    in_progress: Play,
    completed: CheckCircle2,
    failed: CheckCircle2,
  }[node.status];

  return (
    <div
      className="absolute pointer-events-auto"
      style={{ left: node.x, top: node.y, width: 240 }}
    >
      <div
        onClick={onClick}
        className={`
        relative px-4 py-3 rounded-xl border-2 backdrop-blur-xl transition-all duration-300
        hover:scale-105 hover:z-10 cursor-pointer
        ${statusConfig.border} ${statusConfig.bg} ${statusConfig.glow}
        ${isSelected ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-[#0a0e1a] scale-105 z-10' : ''}
      `}>
        {/* Status indicator dot */}
        <div className={`absolute top-2 right-2 w-2 h-2 rounded-full ${statusConfig.dot}`} />

        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <div className={`p-1.5 rounded-lg bg-black/30 ${statusConfig.icon}`}>
            <StatusIcon className="w-4 h-4" />
          </div>
          <span className={`text-sm font-semibold ${statusConfig.text} flex-1 line-clamp-2 leading-tight`}>
            {node.label}
          </span>
        </div>

        {/* Complexity indicator */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[10px] text-gray-400">
            <span>Complexity</span>
            <span className="font-mono tabular-nums">{node.complexity}/10</span>
          </div>
          <div className="flex gap-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div
                key={i}
                className={`h-1.5 flex-1 rounded-full transition-all ${
                  i < node.complexity
                    ? `${statusConfig.dot} opacity-80`
                    : 'bg-gray-700/50 opacity-40'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Bottom accent line */}
        <div className={`absolute bottom-0 left-0 right-0 h-1 rounded-b-xl ${statusConfig.bg} opacity-50`} />
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full ${color}`} />
      <span className="text-gray-500">{label}</span>
    </div>
  );
}
