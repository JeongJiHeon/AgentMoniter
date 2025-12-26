import { PersonalizationPanel } from '../components/personalization/PersonalizationPanel';
import { useChatStore } from '../stores';
import type { PersonalizationItem } from '../types';

export function PersonalizationPage() {
  const { personalizationItems, addPersonalizationItem, updatePersonalizationItem, deletePersonalizationItem } = useChatStore();

  const handleAddItem = (item: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newItem: PersonalizationItem = {
      ...item,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    addPersonalizationItem(newItem);
  };

  return (
    <PersonalizationPanel
      items={personalizationItems}
      onAddItem={handleAddItem}
      onUpdateItem={updatePersonalizationItem}
      onDeleteItem={deletePersonalizationItem}
    />
  );
}
