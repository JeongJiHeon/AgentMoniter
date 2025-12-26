import { useNotificationStore } from '../../stores/notificationStore';

export function ToastContainer() {
  const { toasts, removeToast } = useNotificationStore();

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 min-w-[300px] max-w-md animate-slide-in ${
            toast.type === 'success'
              ? 'bg-green-500/90 text-white'
              : toast.type === 'error'
              ? 'bg-red-500/90 text-white'
              : toast.type === 'warning'
              ? 'bg-yellow-500/90 text-white'
              : 'bg-blue-500/90 text-white'
          }`}
        >
          <div className="flex-1">{toast.message}</div>
          <button
            onClick={() => removeToast(toast.id)}
            className="text-white/80 hover:text-white transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
