import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  ko: {
    translation: {
      dashboard: '대시보드',
      tasks: '작업',
      personalization: '개인화',
      settings: '설정',
      agents: '에이전트',
      active_agents: '활성 에이전트',
      pending_tasks: '대기 중',
      in_progress: '진행 중',
      completed: '완료',
      approval_pending: '승인 대기',
    },
  },
  en: {
    translation: {
      dashboard: 'Dashboard',
      tasks: 'Tasks',
      personalization: 'Personalization',
      settings: 'Settings',
      agents: 'Agents',
      active_agents: 'Active Agents',
      pending_tasks: 'Pending',
      in_progress: 'In Progress',
      completed: 'Completed',
      approval_pending: 'Pending Approval',
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: 'ko',
  fallbackLng: 'ko',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
