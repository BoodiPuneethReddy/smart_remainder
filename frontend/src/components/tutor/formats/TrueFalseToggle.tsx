import React from 'react';
import { Check, X } from 'lucide-react';

interface TrueFalseToggleProps {
  onSelectChoice: (choice: string) => void;
  disabled?: boolean;
}

export default function TrueFalseToggle({
  onSelectChoice,
  disabled = false
}: TrueFalseToggleProps) {
  return (
    <div className="space-y-3">
      <div className="text-[11px] font-mono text-orange-400 uppercase tracking-wider text-center">
        Assertion Verification (Select True or False):
      </div>
      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={() => onSelectChoice("True")}
          disabled={disabled}
          className="py-4 px-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 text-emerald-400 font-bold text-body-lg transition-all flex items-center justify-center gap-2 shadow-lg hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <Check size={20} /> True
        </button>
        <button
          onClick={() => onSelectChoice("False")}
          disabled={disabled}
          className="py-4 px-6 rounded-2xl bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 text-red-400 font-bold text-body-lg transition-all flex items-center justify-center gap-2 shadow-lg hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <X size={20} /> False
        </button>
      </div>
    </div>
  );
}
