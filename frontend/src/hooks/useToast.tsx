/**
 * hooks/useToast.tsx — Global Toast notification state management.
 */
import React, { createContext, useContext, useState, useCallback } from 'react';
import { ToastContainer, type ToastData } from '@/components/ui';

let _toastId = 0;

interface ToastContextType {
  toasts: ToastData[];
  addToast: (toast: Omit<ToastData, 'id'>) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);

  const addToast = useCallback((toast: Omit<ToastData, 'id'>) => {
    const id = String(++_toastId);
    setToasts((prev) => [...prev.slice(-4), { ...toast, id }]); // max 5 toasts
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    // Fallback for components unmounted outside provider
    return {
      toasts: [],
      addToast: () => {},
      dismissToast: () => {},
    };
  }
  return context;
}

