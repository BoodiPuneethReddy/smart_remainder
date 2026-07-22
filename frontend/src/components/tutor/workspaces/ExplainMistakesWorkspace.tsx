import React from 'react';
import { AlertTriangle, CheckCircle2, FileText, ArrowRight } from 'lucide-react';
import ShortAnswerInput from '../formats/ShortAnswerInput';

interface ExplainMistakesWorkspaceProps {
  topic: string;
  misconceptionText?: string;
  onSubmitRemediation: (answer: string) => void;
  disabled?: boolean;
}

export default function ExplainMistakesWorkspace({
  topic,
  misconceptionText = "Asserted that Normalization increases data redundancy, whereas it is specifically designed to eliminate redundancy and anomalies.",
  onSubmitRemediation,
  disabled = false
}: ExplainMistakesWorkspaceProps) {
  return (
    <div className="flex-1 p-6 overflow-y-auto space-y-6 max-w-3xl mx-auto w-full">
      {/* Error Diagnostic Banner */}
      <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 space-y-2 shadow-lg">
        <div className="flex items-center gap-2 text-caption font-bold uppercase tracking-wider text-red-400">
          <AlertTriangle size={18} /> Recorded Misconception Diagnostic
        </div>
        <p className="text-body-sm leading-relaxed font-sans text-red-200">
          "{misconceptionText}"
        </p>
      </div>

      {/* Root Cause Explanation Card */}
      <div className="p-5 rounded-2xl bg-white/5 border border-white/10 space-y-3">
        <div className="text-caption font-bold text-orange-400 uppercase tracking-wider flex items-center gap-2">
          <FileText size={16} /> Root Cause Remediation Guide
        </div>
        <p className="text-body-sm text-white/80 leading-relaxed font-sans">
          Normalization works by decomposing larger unnormalized tables into smaller, well-structured relations connected via foreign keys. This prevents data duplication and protects database integrity during insertion, update, and deletion operations.
        </p>
      </div>

      {/* Targeted Verification Exercise */}
      <div className="space-y-3 pt-2">
        <div className="text-caption font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
          <CheckCircle2 size={16} /> Corrective Remediation Exercise
        </div>
        <div className="text-body-sm font-semibold text-white">
          Explain in your own words how splitting tables prevents update anomalies:
        </div>
        <ShortAnswerInput onSubmitShortAnswer={onSubmitRemediation} disabled={disabled} />
      </div>
    </div>
  );
}
