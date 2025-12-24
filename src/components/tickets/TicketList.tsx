import type { Ticket, TicketStatus } from '../../types';
import { TicketCard } from './TicketCard';

interface TicketListProps {
  tickets: Ticket[];
  filter?: TicketStatus | 'all';
  onApprove?: (ticketId: string) => void;
  onReject?: (ticketId: string) => void;
  onSelectOption?: (ticketId: string, optionId: string) => void;
}

export function TicketList({
  tickets,
  filter = 'all',
  onApprove,
  onReject,
  onSelectOption,
}: TicketListProps) {
  // MECE 구분: 옵션이 있는 티켓은 승인 대기에서만 표시되므로 티켓 목록에서는 제외
  const filteredTickets = filter === 'all'
    ? tickets.filter(t => !(t.status === 'pending_approval' && t.options && t.options.length > 0))
    : tickets.filter(t => t.status === filter && !(t.status === 'pending_approval' && t.options && t.options.length > 0));

  const groupedTickets = groupByStatus(filteredTickets);

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">티켓 목록</h2>
        <div className="flex items-center gap-2">
          <StatusBadge status="pending_approval" count={groupedTickets.pending_approval?.length || 0} />
          <StatusBadge status="in_progress" count={groupedTickets.in_progress?.length || 0} />
        </div>
      </div>

      {/* Pending Approval - 우선 표시 */}
      {groupedTickets.pending_approval && groupedTickets.pending_approval.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-medium text-amber-400 uppercase mb-3 flex items-center gap-2">
            <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
            승인 대기 중
          </h3>
          <div className="space-y-3">
            {groupedTickets.pending_approval.map(ticket => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                onApprove={() => onApprove?.(ticket.id)}
                onReject={() => onReject?.(ticket.id)}
                onSelectOption={(optionId) => onSelectOption?.(ticket.id, optionId)}
              />
            ))}
          </div>
        </div>
      )}

      {/* In Progress */}
      {groupedTickets.in_progress && groupedTickets.in_progress.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-medium text-blue-400 uppercase mb-3">
            진행 중
          </h3>
          <div className="space-y-3">
            {groupedTickets.in_progress.map(ticket => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          </div>
        </div>
      )}

      {/* Completed */}
      {groupedTickets.completed && groupedTickets.completed.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-slate-500 uppercase mb-3">
            완료됨
          </h3>
          <div className="space-y-2">
            {groupedTickets.completed.slice(0, 5).map(ticket => (
              <CompactTicketRow key={ticket.id} ticket={ticket} />
            ))}
          </div>
        </div>
      )}

      {filteredTickets.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          티켓이 없습니다
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status, count }: { status: TicketStatus; count: number }) {
  if (count === 0) return null;

  const config: Record<string, string> = {
    pending_approval: 'bg-amber-500/20 text-amber-400',
    in_progress: 'bg-blue-500/20 text-blue-400',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs ${config[status]}`}>
      {count}
    </span>
  );
}

function CompactTicketRow({ ticket }: { ticket: Ticket }) {
  return (
    <div className="flex items-center justify-between p-2 bg-slate-800 rounded-lg">
      <span className="text-sm text-slate-400 truncate">{ticket.purpose}</span>
      <span className="text-xs text-slate-600">
        {new Date(ticket.updatedAt).toLocaleDateString('ko-KR')}
      </span>
    </div>
  );
}

function groupByStatus(tickets: Ticket[]): Record<TicketStatus, Ticket[]> {
  return tickets.reduce((acc, ticket) => {
    if (!acc[ticket.status]) {
      acc[ticket.status] = [];
    }
    acc[ticket.status].push(ticket);
    return acc;
  }, {} as Record<TicketStatus, Ticket[]>);
}
