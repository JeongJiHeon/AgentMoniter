import { useState } from 'react';
import type { MCPService } from '../../types';
import { MCPServiceCard } from './MCPServiceCard';
import { AddMCPModal } from './AddMCPModal';
import { ConfigureMCPModal } from './ConfigureMCPModal';

interface MCPSettingsProps {
  services: MCPService[];
  onAddService: (service: Omit<MCPService, 'id' | 'status' | 'lastConnected'>) => void;
  onUpdateService: (id: string, updates: Partial<MCPService>) => void;
  onRemoveService: (id: string) => void;
  onConnectService: (id: string) => void;
  onDisconnectService: (id: string) => void;
}

export function MCPSettings({
  services,
  onAddService,
  onUpdateService,
  onRemoveService,
  onConnectService,
  onDisconnectService,
}: MCPSettingsProps) {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [configureServiceId, setConfigureServiceId] = useState<string | null>(null);

  const connectedCount = services.filter(s => s.status === 'connected').length;
  const enabledCount = services.filter(s => s.enabled).length;

  const handleToggle = (id: string, enabled: boolean) => {
    onUpdateService(id, { enabled });
  };

  const serviceToConfig = configureServiceId
    ? services.find(s => s.id === configureServiceId)
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">MCP 서비스</h2>
          <p className="text-sm text-slate-400">
            연결: {connectedCount}/{enabledCount} 활성화
          </p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium flex items-center gap-2"
        >
          <span>+</span>
          MCP 추가
        </button>
      </div>

      {/* Service Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {services.map(service => (
          <MCPServiceCard
            key={service.id}
            service={service}
            onToggle={handleToggle}
            onConnect={onConnectService}
            onDisconnect={onDisconnectService}
            onConfigure={setConfigureServiceId}
            onRemove={onRemoveService}
          />
        ))}
      </div>

      {services.length === 0 && (
        <div className="text-center py-12 text-slate-500">
          <p className="mb-4">등록된 MCP 서비스가 없습니다</p>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg"
          >
            첫 번째 MCP 추가하기
          </button>
        </div>
      )}

      {/* Add Modal */}
      <AddMCPModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={onAddService}
        existingTypes={services.map(s => s.type)}
      />

      {/* Configure Modal */}
      {serviceToConfig && (
        <ConfigureMCPModal
          service={serviceToConfig}
          onClose={() => setConfigureServiceId(null)}
          onSave={(updates) => {
            onUpdateService(serviceToConfig.id, updates);
            setConfigureServiceId(null);
          }}
        />
      )}
    </div>
  );
}
