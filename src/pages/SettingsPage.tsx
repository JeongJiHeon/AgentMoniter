import { SettingsPanel } from '../components/settings/SettingsPanel';
import { useAgentStore, useSettingsStore } from '../stores';

export function SettingsPage() {
  const { settings, updateSettings } = useSettingsStore();
  const { customAgents, updateCustomAgent, deleteCustomAgent } = useAgentStore();

  return (
    <SettingsPanel
      settings={settings}
      customAgents={customAgents}
      onUpdateSettings={updateSettings}
      onUpdateAgent={updateCustomAgent}
      onDeleteAgent={deleteCustomAgent}
    />
  );
}
