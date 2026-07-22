import React, { useState } from 'react';
import { Send, CheckSquare } from 'lucide-react';

interface ShortAnswerInputProps {
  onSubmitShortAnswer: (text: string) => void;
  disabled?: boolean;
}

export default function ShortAnswerInput({
  onSubmitShortAnswer,
  disabled = false
}: ShortAnswerInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (!text.trim()) return;
    onSubmitShortAnswer(text.trim());
    setText('');
  };

  return (
    <div className="flex items-center gap-3">
      <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20 text-orange-400 shrink-0">
        <CheckSquare size={18} />
      </div>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Type concise explanation..."
        className="flex-1 p-3.5 rounded-xl border border-white/10 bg-[#0B0E14] text-white text-body-sm focus:outline-none focus:border-orange-500/50 font-sans"
        disabled={disabled}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        className="p-3.5 rounded-xl bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-30 transition-colors shrink-0"
      >
        <Send size={18} />
      </button>
    </div>
  );
}
