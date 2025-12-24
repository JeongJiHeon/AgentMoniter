/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'agent-idle': '#6B7280',
        'agent-exploring': '#3B82F6',
        'agent-structuring': '#8B5CF6',
        'agent-validating': '#F59E0B',
        'agent-summarizing': '#10B981',
        'ticket-pending': '#EF4444',
        'ticket-approved': '#22C55E',
        'ticket-in-progress': '#3B82F6',
      },
    },
  },
  plugins: [],
}
