import { useState, useEffect } from 'react';
import {
  X, Wrench, Brain, Database, MessageSquare, Target, GitBranch,
  Activity, Zap
} from 'lucide-react';
import type { Task } from '../../types/task';
import type { Agent, AgentLog } from '../../types';
import { useTaskStore } from '../../stores/taskStore';
import { useWebSocketStore } from '../../stores/websocketStore';

interface AgentInsightsPanelProps {
  task?: Task;
  agents: Agent[];
  agentLogs: AgentLog[];
  onClose: () => void;
}

type InsightTab = 'tools' | 'reasoning' | 'memory' | 'context' | 'critique' | 'subagents';

export function AgentInsightsPanel({ task, agents, agentLogs, onClose }: AgentInsightsPanelProps) {
  const [activeTab, setActiveTab] = useState<InsightTab>('tools');
  const { requestAgentMemory } = useWebSocketStore();

  // Get assigned agent
  const assignedAgent = task?.assignedAgentId 
    ? agents.find(a => a.id === task.assignedAgentId)
    : null;

  // Request agent memory when task/agent changes
  useEffect(() => {
    if (assignedAgent?.id && task?.id) {
      requestAgentMemory(assignedAgent.id, task.id);
    }
  }, [assignedAgent?.id, task?.id, requestAgentMemory]);

  const tabs: { id: InsightTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: 'tools', label: 'Tools', icon: Wrench },
    { id: 'reasoning', label: 'Reasoning', icon: Brain },
    { id: 'memory', label: 'Memory', icon: Database },
    { id: 'context', label: 'Context', icon: MessageSquare },
    { id: 'critique', label: 'Critique', icon: Target },
    { id: 'subagents', label: 'Sub-agents', icon: GitBranch },
  ];

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-400/10 flex items-center justify-between">
        <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">Agent Insights</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-red-500/10 rounded border border-transparent hover:border-red-400/30 transition-colors text-gray-400 hover:text-red-400"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-cyan-400/10 overflow-x-auto">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors whitespace-nowrap
                ${activeTab === tab.id
                  ? 'text-cyan-300 bg-cyan-500/10 border-b-2 border-cyan-400'
                  : 'text-gray-500 hover:text-gray-400 hover:bg-gray-800/30'
                }
              `}
            >
              <Icon className="w-3 h-3" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {!task ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <Activity className="w-12 h-12 mb-3 opacity-20" />
            <p className="text-sm text-center">Select a task to view insights</p>
          </div>
        ) : (
          <>
            {activeTab === 'tools' && <ToolsTab task={task} agentLogs={agentLogs} />}
            {activeTab === 'reasoning' && <ReasoningTab task={task} agentLogs={agentLogs} />}
            {activeTab === 'memory' && <MemoryTab task={task} agentId={assignedAgent?.id} />}
            {activeTab === 'context' && <ContextTab task={task} agentLogs={agentLogs} />}
            {activeTab === 'critique' && <CritiqueTab task={task} />}
            {activeTab === 'subagents' && <SubagentsTab task={task} agentLogs={agentLogs} />}
          </>
        )}
      </div>
    </div>
  );
}

// Tool Execution Tab
function ToolsTab({ task, agentLogs }: { task: Task; agentLogs: AgentLog[] }) {
  // Extract tool executions from agent logs
  const taskLogs = agentLogs.filter(log => log.relatedTaskId === task.id);
  
  // Try to extract tool information from logs
  // This is a simple extraction - can be improved based on actual log format
  const toolExecutions = taskLogs
    .filter(log => log.type === 'info' && (log.message.toLowerCase().includes('tool') || log.details?.toLowerCase().includes('tool')))
    .map((log, idx) => {
      // Simple parsing - extract tool name from message/details
      const toolMatch = log.message.match(/(?:tool|Tool):\s*(\w+)/i) || log.details?.match(/(?:tool|Tool):\s*(\w+)/i);
      const toolName = toolMatch ? toolMatch[1] : 'Unknown';
      
      return {
        id: log.id || `tool-${idx}`,
        tool: toolName,
        args: log.details || '',
        status: log.type === 'error' ? 'failed' : 'completed',
        duration: 0, // Duration not available in logs
        output: log.message,
      };
    });

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-3">Tool Execution History</div>

      {toolExecutions.length > 0 ? (
        toolExecutions.map(exec => (
        <div
          key={exec.id}
          className="p-3 rounded-lg bg-gradient-to-br from-gray-800/30 to-gray-900/30 border border-gray-700/30 hover:border-cyan-400/30 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Zap className={`w-3 h-3 ${exec.status === 'in_progress' ? 'text-cyan-400 animate-pulse' : 'text-emerald-400'}`} />
              <span className="text-sm font-medium text-cyan-300 font-mono">{exec.tool}</span>
            </div>
            {exec.duration > 0 && (
              <span className="text-xs text-gray-500 tabular-nums">{exec.duration}ms</span>
            )}
          </div>

          <div className="text-xs text-gray-400 mb-1 font-mono">
            Args: <span className="text-amber-300">{exec.args}</span>
          </div>

          {exec.output && (
            <div className="text-xs text-gray-500 mt-2 p-2 bg-black/30 rounded border border-gray-800">
              {exec.output}
            </div>
          )}
        </div>
      ))
      ) : (
        <div className="text-center py-8 text-gray-600">
          <Zap className="w-12 h-12 mb-3 opacity-20 mx-auto" />
          <p className="text-sm">No tool executions found</p>
          <p className="text-xs text-gray-700 mt-1">Tool executions will appear when agents use tools</p>
        </div>
      )}

      {toolExecutions.length > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-cyan-500/5 border border-cyan-400/20">
          <div className="text-xs text-cyan-300 font-medium mb-2">Tool Statistics</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="text-gray-500">
              Total Calls: <span className="text-gray-300 font-bold">{toolExecutions.length}</span>
            </div>
            <div className="text-gray-500">
              Success Rate: <span className="text-emerald-400 font-bold">
                {toolExecutions.filter(e => e.status === 'completed').length / toolExecutions.length * 100}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Reasoning Chain Tab
function ReasoningTab({ task, agentLogs }: { task: Task; agentLogs: AgentLog[] }) {
  // Extract reasoning steps from agent logs (decision and info type logs)
  const taskLogs = agentLogs.filter(log => log.relatedTaskId === task.id);
  
  // Filter logs that represent reasoning/decision making
  const reasoningSteps = taskLogs
    .filter(log => log.type === 'decision' || (log.type === 'info' && (log.message.includes('Planning') || log.message.includes('계획') || log.details)))
    .map((log, idx) => {
      // Determine type based on log content
      let stepType = 'thought';
      if (log.type === 'decision') {
        stepType = 'plan';
      } else if (log.message.includes('작업 시작') || log.message.includes('Executing')) {
        stepType = 'action';
      } else if (log.message.includes('완료') || log.message.includes('Found') || log.message.includes('결과')) {
        stepType = 'observation';
      }

      return {
        id: log.id || `reasoning-${idx}`,
        type: stepType,
        content: log.message + (log.details ? `\n${log.details}` : ''),
      };
    });

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-3">Chain-of-Thought Process</div>

      {reasoningSteps.length > 0 ? (
        reasoningSteps.map((step, idx) => (
        <div key={step.id} className="flex gap-2">
          <div className="flex flex-col items-center">
            <div className={`
              w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold
              ${step.type === 'thought' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/30' :
                step.type === 'plan' ? 'bg-magenta-500/20 text-magenta-300 border border-magenta-400/30' :
                step.type === 'action' ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30' :
                'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
              }
            `}>
              {idx + 1}
            </div>
            {idx < reasoningSteps.length - 1 && (
              <div className="w-0.5 flex-1 bg-gradient-to-b from-cyan-400/30 to-transparent my-1" />
            )}
          </div>

          <div className="flex-1 pb-3">
            <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">{step.type}</div>
            <div className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">{step.content}</div>
          </div>
        </div>
      ))
      ) : (
        <div className="text-center py-8 text-gray-600">
          <Brain className="w-12 h-12 mb-3 opacity-20 mx-auto" />
          <p className="text-sm">No reasoning data available</p>
          <p className="text-xs text-gray-700 mt-1">Reasoning steps will appear when agents make decisions</p>
        </div>
      )}
    </div>
  );
}

// Memory Tab
function MemoryTab({ task: _task, agentId }: { task: Task; agentId?: string }) {
  const { getAgentMemory } = useTaskStore();

  // Get memory data from store
  const memoryData = agentId ? getAgentMemory(agentId) : undefined;
  const memories = memoryData?.memories || [];
  const stats = memoryData?.stats || { short_term: 0, long_term: 0 };

  // Helper function to map memory type
  function getMemoryTypeLabel(type: string): string {
    const typeMap: Record<string, string> = {
      'fact': 'FACT',
      'pattern': 'PATTERN',
      'preference': 'PREFERENCE',
      'episode': 'EPISODE',
    };
    return typeMap[type] || type.toUpperCase();
  }

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-3">Relevant Memories</div>

      {memories.length > 0 ? (
        memories.map((mem: any, idx: number) => (
          <div
            key={mem.id || mem.memory_id || idx}
            className="p-3 rounded-lg bg-gradient-to-br from-magenta-500/5 to-purple-500/5 border border-magenta-400/20"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-magenta-300 uppercase tracking-wide font-medium">
                {getMemoryTypeLabel(mem.type || mem.memory_type || 'unknown')}
              </span>
              <div className="flex items-center gap-1">
                <div className="text-[10px] text-gray-500">Importance</div>
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }).map((_, i) => {
                    const importance = mem.importance || 0.5;
                    return (
                      <div
                        key={i}
                        className={`w-1 h-3 rounded-full ${
                          i < importance * 5 ? 'bg-magenta-400' : 'bg-gray-700'
                        }`}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
            <div className="text-xs text-gray-300">{mem.content || mem.memory_content || ''}</div>
          </div>
        ))
      ) : (
        <div className="text-center py-8 text-gray-600">
          <Database className="w-12 h-12 mb-3 opacity-20 mx-auto" />
          <p className="text-sm">No memory data available</p>
          <p className="text-xs text-gray-700 mt-1">Memory will appear when agent processes tasks</p>
        </div>
      )}

      <div className="mt-4 p-3 rounded-lg bg-magenta-500/5 border border-magenta-400/20">
        <div className="text-xs text-magenta-300 font-medium mb-2">Memory Stats</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="text-gray-500">
            Short-term: <span className="text-gray-300 font-bold">{stats.short_term || 0}</span>
          </div>
          <div className="text-gray-500">
            Long-term: <span className="text-gray-300 font-bold">{stats.long_term || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Context Tab
function ContextTab({ task, agentLogs }: { task: Task; agentLogs: AgentLog[] }) {
  const { getTaskChatMessages } = useTaskStore();
  
  // Get task chat messages and agent logs
  const chatMessages = task?.id ? getTaskChatMessages(task.id) : [];
  const taskLogs = task?.id ? agentLogs.filter(log => log.relatedTaskId === task.id) : [];

  const totalMessages = chatMessages.length;

  // Token usage is not available in current data structure
  // Will show message count instead
  const maxMessages = 100; // Estimated max messages
  const usage = totalMessages > 0 ? Math.min((totalMessages / maxMessages) * 100, 100) : 0;

  return (
    <div className="space-y-3">
      <div className="text-xs text-gray-500 mb-3">Context Window</div>

      {/* Message Stats */}
      <div className="p-4 rounded-lg bg-gradient-to-br from-cyan-500/5 to-blue-500/5 border border-cyan-400/20">
        <div className="text-xs text-cyan-300 font-medium mb-3">Message Statistics</div>
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Total Messages</span>
            <span className="text-gray-300 font-bold tabular-nums">
              {totalMessages}
            </span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
              style={{ width: `${usage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-700/30">
          <div className="text-xs text-gray-500 mb-1">Chat Messages</div>
          <div className="text-2xl font-bold text-cyan-300 tabular-nums">{chatMessages.length}</div>
        </div>
        <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-700/30">
          <div className="text-xs text-gray-500 mb-1">Agent Logs</div>
          <div className="text-2xl font-bold text-amber-300 tabular-nums">{taskLogs.length}</div>
        </div>
      </div>

      {totalMessages === 0 && taskLogs.length === 0 && (
        <div className="text-center py-8 text-gray-600">
          <MessageSquare className="w-12 h-12 mb-3 opacity-20 mx-auto" />
          <p className="text-sm">No context data available</p>
          <p className="text-xs text-gray-700 mt-1">Context will appear when agents interact with the task</p>
        </div>
      )}
    </div>
  );
}

// Self-Critique Tab
function CritiqueTab({ task: _task }: { task: Task }) {
  // Critique data is not available in current system
  // This will be implemented when critique system is integrated
  
  return (
    <div className="space-y-3">
      <div className="text-xs text-gray-500 mb-3">Quality Assessment</div>

      <div className="text-center py-8 text-gray-600">
        <Target className="w-12 h-12 mb-3 opacity-20 mx-auto" />
        <p className="text-sm">No critique data available</p>
        <p className="text-xs text-gray-700 mt-1">Critique will appear when self-evaluation is implemented</p>
      </div>
    </div>
  );
}

// Sub-agents Tab
function SubagentsTab({ task, agentLogs }: { task: Task; agentLogs: AgentLog[] }) {
  // Extract unique agents from logs
  const taskLogs = agentLogs.filter(log => log.relatedTaskId === task.id);
  const agentMap = new Map<string, { name: string; lastStatus: string; lastActivity: Date }>();
  
  taskLogs.forEach(log => {
    if (!agentMap.has(log.agentId)) {
      agentMap.set(log.agentId, {
        name: log.agentName,
        lastStatus: log.type === 'error' ? 'failed' : log.type === 'info' ? 'completed' : 'in_progress',
        lastActivity: log.timestamp,
      });
    } else {
      const agent = agentMap.get(log.agentId)!;
      // Update status based on latest log
      if (log.type === 'error') {
        agent.lastStatus = 'failed';
      } else if (log.type === 'info' && log.message.includes('완료')) {
        agent.lastStatus = 'completed';
      }
      if (log.timestamp > agent.lastActivity) {
        agent.lastActivity = log.timestamp;
      }
    }
  });

  const subagents = Array.from(agentMap.entries()).map(([id, data]) => ({
    id,
    name: data.name,
    status: data.lastStatus,
    level: 0, // Flat hierarchy for now
  }));

  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-3">Agent Activity</div>

      {subagents.length > 0 ? (
        subagents.map(agent => (
          <div
            key={agent.id}
            className="flex items-center gap-2"
            style={{ paddingLeft: `${agent.level * 16}px` }}
          >
            <div className={`
              flex-1 p-2 rounded-lg border transition-colors
              ${agent.status === 'completed' ? 'bg-emerald-500/10 border-emerald-400/30' :
                agent.status === 'in_progress' ? 'bg-cyan-500/10 border-cyan-400/30' :
                agent.status === 'failed' ? 'bg-red-500/10 border-red-400/30' :
                'bg-gray-800/30 border-gray-700/30'
              }
            `}>
              <div className="flex items-center gap-2">
                <GitBranch className={`w-3 h-3 ${
                  agent.status === 'completed' ? 'text-emerald-400' :
                  agent.status === 'in_progress' ? 'text-cyan-400' :
                  agent.status === 'failed' ? 'text-red-400' :
                  'text-gray-500'
                }`} />
                <span className="text-xs font-medium text-gray-300">{agent.name}</span>
                <span className={`text-[10px] uppercase ${
                  agent.status === 'completed' ? 'text-emerald-400' :
                  agent.status === 'in_progress' ? 'text-cyan-400' :
                  agent.status === 'failed' ? 'text-red-400' :
                  'text-gray-500'
                }`}>
                  {agent.status}
                </span>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center py-8 text-gray-600">
          <GitBranch className="w-12 h-12 mb-3 opacity-20 mx-auto" />
          <p className="text-sm">No agent activity found</p>
          <p className="text-xs text-gray-700 mt-1">Agent activity will appear when agents process the task</p>
        </div>
      )}
    </div>
  );
}


