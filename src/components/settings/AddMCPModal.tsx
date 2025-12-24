import { useState } from 'react';
import type { MCPServiceType, MCPService } from '../../types';

interface AddMCPModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (service: Omit<MCPService, 'id' | 'status' | 'lastConnected'>) => void;
  existingTypes: MCPServiceType[];
}

interface MCPTemplate {
  type: MCPServiceType;
  name: string;
  description: string;
  icon: string;
  configFields: Array<{
    key: string;
    label: string;
    type: 'text' | 'password' | 'url';
    required: boolean;
    placeholder: string;
  }>;
}

const mcpTemplates: MCPTemplate[] = [
  {
    type: 'notion',
    name: 'Notion',
    description: 'Notion 워크스페이스와 연동하여 페이지를 관리합니다',
    icon: 'N',
    configFields: [
      { key: 'apiKey', label: 'API Key', type: 'password', required: true, placeholder: 'secret_...' },
      { key: 'workspaceId', label: 'Workspace ID', type: 'text', required: false, placeholder: '선택사항' },
    ],
  },
  {
    type: 'slack',
    name: 'Slack',
    description: 'Slack 워크스페이스와 연동하여 메시지를 관리합니다',
    icon: 'S',
    configFields: [
      { key: 'accessToken', label: 'Bot Token', type: 'password', required: true, placeholder: 'xoxb-...' },
      { key: 'webhookUrl', label: 'Webhook URL', type: 'url', required: false, placeholder: 'https://hooks.slack.com/...' },
    ],
  },
  {
    type: 'confluence',
    name: 'Confluence',
    description: 'Confluence 페이지와 연동하여 문서를 관리합니다',
    icon: 'C',
    configFields: [
      { key: 'baseUrl', label: 'Base URL', type: 'url', required: true, placeholder: 'https://your-domain.atlassian.net' },
      { key: 'apiKey', label: 'API Token', type: 'password', required: true, placeholder: 'API Token' },
      { key: 'email', label: 'Email', type: 'text', required: true, placeholder: 'user@example.com' },
    ],
  },
  {
    type: 'gmail',
    name: 'Gmail',
    description: 'Gmail과 연동하여 이메일을 관리합니다',
    icon: 'G',
    configFields: [
      { key: 'accessToken', label: 'OAuth Token', type: 'password', required: true, placeholder: 'OAuth 인증 필요' },
    ],
  },
  {
    type: 'jira',
    name: 'Jira',
    description: 'Jira와 연동하여 이슈를 관리합니다',
    icon: 'J',
    configFields: [
      { key: 'baseUrl', label: 'Base URL', type: 'url', required: true, placeholder: 'https://your-domain.atlassian.net' },
      { key: 'apiKey', label: 'API Token', type: 'password', required: true, placeholder: 'API Token' },
      { key: 'email', label: 'Email', type: 'text', required: true, placeholder: 'user@example.com' },
    ],
  },
  {
    type: 'github',
    name: 'GitHub',
    description: 'GitHub와 연동하여 저장소를 관리합니다',
    icon: 'H',
    configFields: [
      { key: 'accessToken', label: 'Personal Access Token', type: 'password', required: true, placeholder: 'ghp_...' },
    ],
  },
  {
    type: 'custom',
    name: 'Custom MCP',
    description: '커스텀 MCP 서버에 연결합니다',
    icon: '*',
    configFields: [
      { key: 'baseUrl', label: 'Server URL', type: 'url', required: true, placeholder: 'http://localhost:3000' },
      { key: 'apiKey', label: 'API Key', type: 'password', required: false, placeholder: '선택사항' },
    ],
  },
];

export function AddMCPModal({ isOpen, onClose, onAdd, existingTypes }: AddMCPModalProps) {
  const [step, setStep] = useState<'select' | 'configure'>('select');
  const [selectedTemplate, setSelectedTemplate] = useState<MCPTemplate | null>(null);
  const [config, setConfig] = useState<Record<string, string>>({});
  const [customName, setCustomName] = useState('');

  if (!isOpen) return null;

  const availableTemplates = mcpTemplates.filter(t => !existingTypes.includes(t.type) || t.type === 'custom');

  const handleSelectTemplate = (template: MCPTemplate) => {
    setSelectedTemplate(template);
    setCustomName(template.name);
    setConfig({});
    setStep('configure');
  };

  const handleAdd = () => {
    if (!selectedTemplate) return;

    onAdd({
      type: selectedTemplate.type,
      name: customName || selectedTemplate.name,
      description: selectedTemplate.description,
      enabled: true,
      config,
    });

    // Reset
    setStep('select');
    setSelectedTemplate(null);
    setConfig({});
    setCustomName('');
    onClose();
  };

  const handleClose = () => {
    setStep('select');
    setSelectedTemplate(null);
    setConfig({});
    setCustomName('');
    onClose();
  };

  const isConfigValid = () => {
    if (!selectedTemplate) return false;
    return selectedTemplate.configFields
      .filter(f => f.required)
      .every(f => config[f.key]?.trim());
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-lg max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">
            {step === 'select' ? 'MCP 서비스 추가' : `${selectedTemplate?.name} 설정`}
          </h2>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white"
          >
            닫기
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {step === 'select' && (
            <div className="grid grid-cols-2 gap-3">
              {availableTemplates.map(template => (
                <button
                  key={template.type}
                  onClick={() => handleSelectTemplate(template)}
                  className="p-4 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-left transition-colors border border-slate-600 hover:border-slate-500"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 bg-blue-500/20 text-blue-400 rounded flex items-center justify-center font-bold">
                      {template.icon}
                    </div>
                    <span className="font-medium text-white">{template.name}</span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{template.description}</p>
                </button>
              ))}
            </div>
          )}

          {step === 'configure' && selectedTemplate && (
            <div className="space-y-4">
              {/* Service Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  서비스 이름
                </label>
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                  placeholder={selectedTemplate.name}
                />
              </div>

              {/* Config Fields */}
              {selectedTemplate.configFields.map(field => (
                <div key={field.key}>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    {field.label}
                    {field.required && <span className="text-red-400 ml-1">*</span>}
                  </label>
                  <input
                    type={field.type}
                    value={config[field.key] || ''}
                    onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    placeholder={field.placeholder}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'configure' && (
          <div className="px-6 py-4 border-t border-slate-700 flex gap-2 justify-end">
            <button
              onClick={() => setStep('select')}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg"
            >
              뒤로
            </button>
            <button
              onClick={handleAdd}
              disabled={!isConfigValid()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              추가
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
