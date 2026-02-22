import { useStore } from "../../store/useStore";

const TYPE_STYLES = {
  success: "border-green-500/50 bg-green-900/30 text-green-300",
  error: "border-red-500/50 bg-red-900/30 text-red-300",
  warning: "border-yellow-500/50 bg-yellow-900/30 text-yellow-300",
};

const TYPE_STYLES_LIGHT = {
  success: "border-green-400 bg-green-50 text-green-800",
  error: "border-red-400 bg-red-50 text-red-800",
  warning: "border-yellow-400 bg-yellow-50 text-yellow-800",
};

export default function ToastContainer() {
  const { toasts, removeToast, theme } = useStore();
  const styles = theme === "light" ? TYPE_STYLES_LIGHT : TYPE_STYLES;

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto px-4 py-2 rounded border shadow-lg text-sm
                      flex items-center gap-3 animate-slide-in ${styles[toast.type]}`}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="opacity-60 hover:opacity-100 text-xs cursor-pointer"
          >
            &#10005;
          </button>
        </div>
      ))}
    </div>
  );
}
