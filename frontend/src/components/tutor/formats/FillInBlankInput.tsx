import React, { useState } from 'react';
import { Send, Edit3 } from 'lucide-react';

interface FillInBlankInputProps {
  onSubmitBlank: (text: string) => void;
  disabled?: boolean;
}

export default function FillInBlankInput({
  onSubmitBlank,
  disabled = false
}: FillInBlankInputProps) {
  const [value, setValue] = useState('');

  const handleSubmit = () => {
    if (!value.trim()) return;
    onSubmitBlank(value.trim());
    setValue('');
  };

  return (
    <div className="flex items-center gap-3">
      <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20 text-orange-400 shrink-0">
        <Edit3 size={18} />
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Type missing term to complete assertion..."
        className="flex-1 p-3.5 rounded-xl border border-white/10 bg-[#0B0E14] text-white text-body-sm focus:outline-none focus:border-orange-500/50 font-sans"
        disabled={disabled}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        className="p-3.5 rounded-xl bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-30 transition-colors shrink-0"
      >
        <Send size={18} />
      </button>
    </div>
  );
}
