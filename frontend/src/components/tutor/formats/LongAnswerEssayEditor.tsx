import React, { useState } from 'react';
import { Send, FileText } from 'lucide-react';

interface LongAnswerEssayEditorProps {
  onSubmitEssay: (essay: string) => void;
  disabled?: boolean;
}

export default function LongAnswerEssayEditor({
  onSubmitEssay,
  disabled = false
}: LongAnswerEssayEditorProps) {
  const [essay, setEssay] = useState('');

  const handleSubmit = () => {
    if (!essay.trim()) return;
    onSubmitEssay(essay.trim());
    setEssay('');
  };

  const wordCount = essay.trim() ? essay.trim().split(/\s+/).length : 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-[11px] font-mono text-orange-400 uppercase tracking-wider">
        <span className="flex items-center gap-1.5"><FileText size={13} /> Multi-Paragraph Essay Workbench</span>
        <span>Word Count: {wordCount} words</span>
      </div>
      <div className="relative">
        <textarea
          rows={4}
          value={essay}
          onChange={(e) => setEssay(e.target.value)}
          placeholder="Write your comprehensive technical response, architectural reasoning, or scenario analysis..."
          className="w-full p-4 rounded-xl border border-white/10 bg-[#0B0E14] text-white text-body-sm focus:outline-none focus:border-orange-500/50 resize-none font-sans leading-relaxed"
          disabled={disabled}
        />
        <div className="mt-2 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={disabled || !essay.trim()}
            className="px-6 py-2.5 rounded-xl bg-orange-500 text-white hover:bg-orange-600 font-semibold text-caption flex items-center gap-2 shadow-lg shadow-orange-500/20 disabled:opacity-30 transition-all"
          >
            <Send size={16} /> Submit Essay Answer
          </button>
        </div>
      </div>
    </div>
  );
}
