"use client";

export interface ToastItem {
  id: number;
  kind: "success" | "error" | "info";
  message: string;
}

const KIND_STYLES = {
  success: "border-teal-200 text-teal-900",
  error: "border-rose-200 text-rose-900",
  info: "border-gray-200 text-slate-900",
} as const;

const DOT_STYLES = {
  success: "bg-teal-600",
  error: "bg-rose-600",
  info: "bg-slate-400",
} as const;

interface ToastStackProps {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}

export default function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      className="fixed right-4 top-20 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role={toast.kind === "error" ? "alert" : "status"}
          className={`pointer-events-auto flex items-start gap-3 rounded-lg border bg-white px-4 py-3 text-sm shadow-lg ${KIND_STYLES[toast.kind]}`}
        >
          <span
            aria-hidden="true"
            className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${DOT_STYLES[toast.kind]}`}
          />
          <p className="flex-1 py-0.5">{toast.message}</p>
          <button
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss"
            className="text-gray-400 transition-colors hover:text-gray-600 cursor-pointer"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}