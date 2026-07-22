/**
 * hooks/useToast.tsx — Toast notification state management.
 */
import { useState, useCallback } from 'react';
import type { ToastData } from '@/components/ui';

let _toastId = 0;

export function useToast() {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const addToast = useCallback((toast: Omit<ToastData, 'id'>) => {
    const id = String(++_toastId);
    setToasts((prev) => [...prev.slice(-4), { ...toast, id }]); // max 5 toasts
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, addToast, dismissToast };
}
