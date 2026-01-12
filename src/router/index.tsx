import { createBrowserRouter, Navigate } from 'react-router-dom';
import App from '../App';
import { EnhancedDashboardPage } from '../pages/EnhancedDashboardPage';
import { EnhancedTasksPage } from '../pages/EnhancedTasksPage';
import { EnhancedPersonalizationPage } from '../pages/EnhancedPersonalizationPage';
import { EnhancedSettingsPage } from '../pages/EnhancedSettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Navigate to="/tasks" replace />,
      },
      {
        path: 'dashboard',
        element: <EnhancedDashboardPage />,
      },
      {
        path: 'tasks',
        element: <EnhancedTasksPage />,
      },
      {
        path: 'personalization',
        element: <EnhancedPersonalizationPage />,
      },
      {
        path: 'settings',
        element: <EnhancedSettingsPage />,
      },
    ],
  },
]);
