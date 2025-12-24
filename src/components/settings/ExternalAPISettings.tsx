import type { ExternalAPI } from '../../types';

interface ExternalAPISettingsProps {
  apis: ExternalAPI[];
  onRefresh: (id: string) => void;
}

const statusConfig = {
  active: { label: '정상', color: 'text-green-400', bgColor: 'bg-green-500/20' },
  inactive: { label: '비활성', color: 'text-slate-400', bgColor: 'bg-slate-500/20' },
  error: { label: '오류', color: 'text-red-400', bgColor: 'bg-red-500/20' },
};

export function ExternalAPISettings({ apis, onRefresh }: ExternalAPISettingsProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-white">외부 API 연동</h2>
        <p className="text-sm text-slate-400">시스템과 연동된 외부 API 상태를 확인합니다</p>
      </div>

      {/* API List */}
      <div className="space-y-3">
        {apis.map(api => {
          const status = statusConfig[api.status];
          return (
            <div
              key={api.id}
              className="bg-slate-800 rounded-lg border border-slate-700 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 font-mono text-xs">
                    API
                  </div>
                  <div>
                    <h3 className="font-medium text-white">{api.name}</h3>
                    <p className="text-xs text-slate-500">{api.type}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded text-xs ${status.bgColor} ${status.color}`}>
                    {status.label}
                  </span>
                  <button
                    onClick={() => onRefresh(api.id)}
                    className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded"
                  >
                    새로고침
                  </button>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-slate-700 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-mono">{api.baseUrl}</span>
                {api.lastHealthCheck && (
                  <span className="text-slate-500">
                    마지막 확인: {new Date(api.lastHealthCheck).toLocaleString('ko-KR')}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {apis.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          연동된 외부 API가 없습니다
        </div>
      )}
    </div>
  );
}
