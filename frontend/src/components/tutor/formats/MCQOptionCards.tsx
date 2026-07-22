import React from 'react';
import { CheckCircle2 } from 'lucide-react';

interface MCQOptionCardsProps {
  options?: string[];
  onSelectOption: (option: string) => void;
  disabled?: boolean;
}

export default function MCQOptionCards({
  options = [
    "Option A: Core Definition & Primary Relation",
    "Option B: Secondary Relation & Key Constraint",
    "Option C: Decomposed Attribute Set",
    "Option D: All of the above"
  ],
  onSelectOption,
  disabled = false
}: MCQOptionCardsProps) {
  return (
    <div className="space-y-3">
      <div className="text-[11px] font-mono text-orange-400 uppercase tracking-wider flex items-center gap-1.5">
        <CheckCircle2 size={13} /> Select Choice Answer:
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {options.map((opt, idx) => (
          <button
            key={idx}
            onClick={() => onSelectOption(opt)}
            disabled={disabled}
            className="p-3.5 rounded-xl border border-white/10 bg-white/5 hover:border-orange-500/50 hover:bg-orange-500/10 text-left text-body-sm text-white font-medium transition-all group flex items-start gap-3 disabled:opacity-50"
          >
            <span className="w-6 h-6 rounded-lg bg-white/10 text-white/70 group-hover:bg-orange-500 group-hover:text-white flex items-center justify-center text-caption font-bold shrink-0 transition-colors">
              {String.fromCharCode(65 + idx)}
            </span>
            <span className="flex-1 mt-0.5">{opt}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
