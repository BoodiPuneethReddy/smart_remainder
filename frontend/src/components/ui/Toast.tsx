/**
 * components/ui/Toast.tsx — Reminder toast notification with spring animation.
 * Used by the ToastProvider for Reminder Agent notifications.
 * Slides in with springIn variant, auto-dismisses after 6s.
 */
import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bell, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springIn } from '@/lib/motion';
import { iconSize } from './Badge';

export interface ToastData {
  id: string;
  title: string;
  message: string;
  urgency_tier: 'critical' | 'high' | 'medium';
  duration?: number;
}

interface ToastProps {
  toast: ToastData;
  onDismiss: (id: string) => void;
}

const tierConfig = {
  critical: { color: 'var(--danger)',  Icon: AlertTriangle, border: 'border-[var(--danger)]' },
  high:     { color: 'var(--warning)', Icon: Bell,           border: 'border-[var(--warning)]' },
  medium:   { color: 'var(--info)',    Icon: Clock,          border: 'border-[var(--info)]' },
};

export function Toast({ toast, onDismiss }: ToastProps) {
  const config = tierConfig[toast.urgency_tier] ?? tierConfig.medium;
  const { Icon, color, border } = config;

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), toast.duration ?? 6000);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <motion.div
      key={toast.id}
      variants={springIn}
      initial="initial"
      animate="animate"
      exit="exit"
      layout
      className={cn(
        'pointer-events-auto w-80 glass rounded-card p-4 shadow-floating',
        'border-l-4', border,
      )}
    >
      <div className="flex items-start gap-3">
        <Icon size={iconSize.button} style={{ color }} className="flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-h3 text-[var(--text-primary)] mb-0.5">{toast.title}</p>
          <p className="text-body-sm text-[var(--text-secondary)] leading-relaxed">{toast.message}</p>
        </div>
        <button
          onClick={() => onDismiss(toast.id)}
          className="flex-shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          <X size={iconSize.inline} />
        </button>
      </div>
    </motion.div>
  );
}

// ── ToastContainer — fixed bottom-right portal ────────────────────────────────
interface ToastContainerProps {
  toasts: ToastData[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none"
      aria-live="polite"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} onDismiss={onDismiss} />
        ))}
      </AnimatePresence>
    </div>
  );
}
