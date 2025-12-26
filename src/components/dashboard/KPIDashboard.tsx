import { useMemo } from 'react';
import { useTaskStore, useTicketStore } from '../../stores';
import { useAllAgents } from '../../hooks/useAllAgents';

export function KPIDashboard() {
  const agents = useAllAgents();
  const tasks = useTaskStore((state) => state.tasks);
  const { tickets, approvalQueue } = useTicketStore();

  // Calculate KPIs
  const kpis = useMemo(() => {
    const activeAgents = agents.filter((a) => a.isActive).length;
    const totalAgents = agents.length;

    const pendingTasks = tasks.filter((t) => t.status === 'pending').length;
    const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;
    const completedTasks = tasks.filter((t) => t.status === 'completed').length;
    const totalTasks = tasks.length;

    const pendingApprovals = approvalQueue.length;
    const pendingTickets = tickets.filter((t) => t.status === 'pending_approval').length;

    // Calculate completion rate
    const completionRate = totalTasks > 0 ? ((completedTasks / totalTasks) * 100).toFixed(1) : '0';

    return {
      activeAgents,
      totalAgents,
      pendingTasks,
      inProgressTasks,
      completedTasks,
      totalTasks,
      pendingApprovals,
      pendingTickets,
      completionRate,
    };
  }, [agents, tasks, tickets, approvalQueue]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Active Agents KPI */}
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">활성 Agent</p>
            <p className="text-3xl font-bold text-white mt-1">
              {kpis.activeAgents}
              <span className="text-lg text-slate-500 font-normal"> / {kpis.totalAgents}</span>
            </p>
          </div>
          <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Tasks KPI */}
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">진행 중인 작업</p>
            <p className="text-3xl font-bold text-white mt-1">
              {kpis.inProgressTasks}
              <span className="text-lg text-slate-500 font-normal"> / {kpis.totalTasks}</span>
            </p>
          </div>
          <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
        </div>
        <div className="mt-2 flex gap-2 text-xs">
          <span className="text-yellow-400">{kpis.pendingTasks} 대기</span>
          <span className="text-blue-400">{kpis.completedTasks} 완료</span>
        </div>
      </div>

      {/* Completion Rate KPI */}
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">완료율</p>
            <p className="text-3xl font-bold text-white mt-1">{kpis.completionRate}%</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
      </div>

      {/* Pending Approvals KPI */}
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-400">승인 대기</p>
            <p className="text-3xl font-bold text-white mt-1">{kpis.pendingApprovals}</p>
          </div>
          <div className="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        {kpis.pendingApprovals > 0 && (
          <div className="mt-2">
            <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-orange-500 rounded-full animate-pulse" style={{ width: '100%' }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
