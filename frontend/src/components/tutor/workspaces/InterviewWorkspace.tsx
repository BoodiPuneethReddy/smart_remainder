import React, { useState } from 'react';
import { UserCheck, Terminal, Award, FileText } from 'lucide-react';
import LongAnswerEssayEditor from '../formats/LongAnswerEssayEditor';

interface InterviewWorkspaceProps {
  topic: string;
  personality: string;
  scenarioText: string;
  onSubmitCandidateAnswer: (answer: string) => void;
  mermaidCode?: string;
  disabled?: boolean;
}

export default function InterviewWorkspace({
  topic,
  personality = "Interviewer",
  scenarioText,
  onSubmitCandidateAnswer,
  mermaidCode,
  disabled = false
}: InterviewWorkspaceProps) {
  return (
    <div className="flex-1 flex flex-col md:flex-row overflow-hidden border-t border-white/10">
      {/* Left Interviewer Persona & System Diagram View */}
      <div className="w-full md:w-1/2 p-6 border-r border-white/10 overflow-y-auto space-y-6 bg-white/2">
        <div className="p-4 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-orange-500 text-white flex items-center justify-center font-bold">
            <UserCheck size={20} />
          </div>
          <div>
            <div className="text-[10px] font-mono text-orange-400 uppercase tracking-wider">Senior Tech Lead Interviewer</div>
            <div className="text-body-md font-bold text-white">System Design Evaluation</div>
          </div>
        </div>

        <div className="space-y-2">
          <h4 className="text-caption font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <FileText size={14} className="text-orange-500" /> Interview Question Scenario
          </h4>
          <div className="p-5 rounded-2xl bg-white/5 border border-white/10 text-body-sm text-white/90 leading-relaxed font-sans shadow-inner">
            {scenarioText || `Suppose you are designing a high-scale architecture for ${topic}. How would you implement database partitioning, zero-downtime migrations, and anomaly protection? Explain your design choices.`}
          </div>
        </div>

        {mermaidCode && (
          <div className="space-y-2">
            <h4 className="text-caption font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Terminal size={14} className="text-emerald-400" /> Proposed System Architecture
            </h4>
            <pre className="p-4 rounded-2xl bg-black/60 text-[11px] font-mono text-emerald-400 overflow-x-auto leading-relaxed border border-white/10">
              {mermaidCode}
            </pre>
          </div>
        )}
      </div>

      {/* Right Technical Response Workbench */}
      <div className="flex-1 p-6 overflow-y-auto flex flex-col justify-between space-y-6">
        <div>
          <h4 className="text-caption font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-2">
            <Award size={14} className="text-amber-400" /> Candidate Response Console
          </h4>
          <p className="text-caption text-white/50 mb-4">
            Structure your response clearly: state assumptions, explain core architectural choices, and justify trade-offs under high scale.
          </p>
        </div>

        <LongAnswerEssayEditor 
          onSubmitEssay={onSubmitCandidateAnswer} 
          disabled={disabled} 
        />
      </div>
    </div>
  );
}
