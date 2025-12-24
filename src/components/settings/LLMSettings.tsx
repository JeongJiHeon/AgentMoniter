import { useState } from 'react';
import type { LLMConfig, LLMModel, LLMProvider } from '../../types';

interface LLMSettingsProps {
  config: LLMConfig;
  availableModels: LLMModel[];
  onUpdateConfig: (config: Partial<LLMConfig>) => void;
}

const providerConfig: Record<LLMProvider, { name: string; icon: string; color: string }> = {
  anthropic: { name: 'Anthropic', icon: 'A', color: 'bg-orange-500/20 text-orange-400' },
  openai: { name: 'OpenAI', icon: 'O', color: 'bg-green-500/20 text-green-400' },
  google: { name: 'Google', icon: 'G', color: 'bg-blue-500/20 text-blue-400' },
  azure: { name: 'Azure OpenAI', icon: 'Z', color: 'bg-cyan-500/20 text-cyan-400' },
  local: { name: 'Local', icon: 'L', color: 'bg-purple-500/20 text-purple-400' },
};

export function LLMSettings({ config, availableModels, onUpdateConfig }: LLMSettingsProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [customModelName, setCustomModelName] = useState('');

  const providers = [...new Set(availableModels.map(m => m.provider))];
  const modelsForProvider = availableModels.filter(m => m.provider === config.provider);

  const handleCustomModelApply = () => {
    if (customModelName.trim()) {
      onUpdateConfig({ model: customModelName.trim() });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-white">LLM 설정</h2>
        <p className="text-sm text-slate-400">Agent가 사용할 언어 모델을 설정합니다</p>
      </div>

      {/* Provider Selection */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Provider
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
          {providers.map(provider => {
            const pConfig = providerConfig[provider];
            const isSelected = config.provider === provider;
            const hasAvailable = availableModels.some(m => m.provider === provider && m.isAvailable);

            return (
              <button
                key={provider}
                onClick={() => onUpdateConfig({ provider })}
                disabled={!hasAvailable}
                className={`
                  p-3 rounded-lg border transition-all text-left
                  ${isSelected
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-600 bg-slate-800 hover:border-slate-500'
                  }
                  ${!hasAvailable ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold ${pConfig.color}`}>
                    {pConfig.icon}
                  </div>
                  <span className="text-sm text-white">{pConfig.name}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Model Selection Mode Toggle */}
      <div className="flex items-center gap-4">
        <label className="block text-sm font-medium text-slate-300">모델</label>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUseCustomModel(false)}
            className={`px-3 py-1 text-xs rounded-lg transition-colors ${
              !useCustomModel
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            목록에서 선택
          </button>
          <button
            onClick={() => setUseCustomModel(true)}
            className={`px-3 py-1 text-xs rounded-lg transition-colors ${
              useCustomModel
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            직접 입력
          </button>
        </div>
      </div>

      {/* Model Selection - List Mode */}
      {!useCustomModel && (
        <div className="space-y-2">
          {modelsForProvider.map(model => (
            <button
              key={model.id}
              onClick={() => onUpdateConfig({ model: model.id })}
              disabled={!model.isAvailable}
              className={`
                w-full p-4 rounded-lg border transition-all text-left
                ${config.model === model.id
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 bg-slate-800 hover:border-slate-500'
                }
                ${!model.isAvailable ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{model.name}</span>
                    {model.isDefault && (
                      <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">
                        기본값
                      </span>
                    )}
                    {!model.isAvailable && (
                      <span className="px-1.5 py-0.5 bg-slate-500/20 text-slate-400 text-xs rounded">
                        사용 불가
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{model.description}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500">
                    {model.maxTokens.toLocaleString()} tokens
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Model Selection - Custom Input Mode */}
      {useCustomModel && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={customModelName}
              onChange={(e) => setCustomModelName(e.target.value)}
              className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              placeholder="모델명 입력 (예: claude-3-5-sonnet-20241022, gpt-4o-2024-08-06)"
            />
            <button
              onClick={handleCustomModelApply}
              disabled={!customModelName.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              적용
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Provider의 공식 모델명을 입력하세요. 현재 선택된 모델: <span className="text-blue-400">{config.model}</span>
          </p>
        </div>
      )}

      {/* API Key */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          API Key
        </label>
        <div className="relative">
          <input
            type={showApiKey ? 'text' : 'password'}
            value={config.apiKey || ''}
            onChange={(e) => onUpdateConfig({ apiKey: e.target.value })}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 pr-20"
            placeholder="API Key 입력"
          />
          <button
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs text-slate-400 hover:text-white"
          >
            {showApiKey ? '숨기기' : '보기'}
          </button>
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="pt-4 border-t border-slate-700">
        <h3 className="text-sm font-medium text-slate-400 mb-4">고급 설정</h3>

        <div className="grid grid-cols-2 gap-4">
          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Temperature: {config.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={config.temperature}
              onChange={(e) => onUpdateConfig({ temperature: parseFloat(e.target.value) })}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>정확함</span>
              <span>창의적</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Max Tokens
            </label>
            <input
              type="number"
              value={config.maxTokens}
              onChange={(e) => onUpdateConfig({ maxTokens: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              min="100"
              max="128000"
              step="100"
            />
          </div>
        </div>

        {/* Custom Base URL */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Base URL (선택사항)
          </label>
          <input
            type="url"
            value={config.baseUrl || ''}
            onChange={(e) => onUpdateConfig({ baseUrl: e.target.value })}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
            placeholder="커스텀 API 엔드포인트"
          />
        </div>
      </div>
    </div>
  );
}
