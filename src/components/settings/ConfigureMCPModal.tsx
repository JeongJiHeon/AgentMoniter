import { useState } from 'react';
import type { MCPService, MCPServiceConfig } from '../../types';

interface ConfigureMCPModalProps {
  service: MCPService;
  onClose: () => void;
  onSave: (updates: Partial<MCPService>) => void;
}

const configFieldsByType: Record<string, Array<{
  key: string;
  label: string;
  type: 'text' | 'password' | 'url';
}>> = {
  notion: [
    { key: 'apiKey', label: 'API Key', type: 'password' },
    { key: 'workspaceId', label: 'Workspace ID', type: 'text' },
  ],
  slack: [
    { key: 'accessToken', label: 'Bot Token', type: 'password' },
    { key: 'webhookUrl', label: 'Webhook URL', type: 'url' },
  ],
  confluence: [
    { key: 'baseUrl', label: 'Base URL', type: 'url' },
    { key: 'apiKey', label: 'API Token', type: 'password' },
    { key: 'email', label: 'Email', type: 'text' },
  ],
  gmail: [
    { key: 'accessToken', label: 'OAuth Token', type: 'password' },
  ],
  jira: [
    { key: 'baseUrl', label: 'Base URL', type: 'url' },
    { key: 'apiKey', label: 'API Token', type: 'password' },
    { key: 'email', label: 'Email', type: 'text' },
  ],
  github: [
    { key: 'accessToken', label: 'Personal Access Token', type: 'password' },
  ],
  custom: [
    { key: 'baseUrl', label: 'Server URL', type: 'url' },
    { key: 'apiKey', label: 'API Key', type: 'password' },
  ],
};

export function ConfigureMCPModal({ service, onClose, onSave }: ConfigureMCPModalProps) {
  const [name, setName] = useState(service.name);
  const [description, setDescription] = useState(service.description);
  const [config, setConfig] = useState<MCPServiceConfig>({ ...service.config });

  const fields = configFieldsByType[service.type] || configFieldsByType.custom;

  const handleSave = () => {
    onSave({
      name,
      description,
      config,
    });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-md">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">{service.name} 설정</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            닫기
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              서비스 이름
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              설명
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Config Fields */}
          <div className="pt-2 border-t border-slate-700">
            <h3 className="text-sm font-medium text-slate-400 mb-3">연결 설정</h3>
            {fields.map(field => (
              <div key={field.key} className="mb-3">
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  value={config[field.key] || ''}
                  onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder={field.type === 'password' ? '••••••••' : ''}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-700 flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"
          >
            저장
          </button>
        </div>
      </div>
    </div>
  );
}
