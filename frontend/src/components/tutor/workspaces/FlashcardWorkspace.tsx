import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, CheckCircle, Flame, Layers } from 'lucide-react';

interface FlashcardWorkspaceProps {
  topic: string;
  question: string;
  answer?: string;
  onRateConfidence: (rating: string) => void;
  disabled?: boolean;
}

export default function FlashcardWorkspace({
  topic,
  question,
  answer,
  onRateConfidence,
  disabled = false
}: FlashcardWorkspaceProps) {
  const [isFlipped, setIsFlipped] = useState(false);

  // Honest state: Display exact answer or clear notice if empty
  const modelAnswerText = answer && answer.trim().length > 0 
    ? answer 
    : "No generated model answer available for this flashcard yet.";

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center gap-2 text-caption font-mono text-orange-400 uppercase tracking-wider">
        <Layers size={16} /> Flashcard Recall Deck: <span className="text-white font-bold">{topic}</span>
      </div>

      {/* 3D Flip Card */}
      <div 
        onClick={() => setIsFlipped(!isFlipped)}
        className="w-full h-72 cursor-pointer perspective-1000"
      >
        <motion.div
          animate={{ rotateY: isFlipped ? 180 : 0 }}
          transition={{ duration: 0.6, type: "spring", stiffness: 260, damping: 20 }}
          className="w-full h-full relative transform-style-3d shadow-2xl rounded-3xl"
        >
          {/* Front Side */}
          <div className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-br from-white/10 to-white/5 border border-white/15 p-8 flex flex-col justify-between backdrop-blur-xl backface-hidden">
            <div className="flex items-center justify-between text-[11px] font-mono text-white/40">
              <span>CARD FRONT</span>
              <span className="text-orange-400">Click to flip 🔄</span>
            </div>
            <div className="text-h3 font-bold text-white text-center leading-relaxed">
              {question || `Define the key architectural principles of ${topic}`}
            </div>
            <div className="text-[11px] text-center text-white/40 italic">
              Try to recall the definition and key keywords before flipping.
            </div>
          </div>

          {/* Back Side */}
          <div className="absolute inset-0 w-full h-full rounded-3xl bg-gradient-to-br from-orange-950/40 to-black/80 border border-orange-500/30 p-8 flex flex-col justify-between backdrop-blur-xl backface-hidden rotate-y-180">
            <div className="flex items-center justify-between text-[11px] font-mono text-orange-400 font-bold">
              <span>CARD BACK — MODEL ANSWER</span>
              <CheckCircle size={14} className="text-emerald-400" />
            </div>
            <div className="text-body-md text-orange-100 text-center leading-relaxed font-sans">
              {modelAnswerText}
            </div>
            <div className="text-[11px] text-center text-emerald-400 font-mono">
              Recall keywords verified against syllabus.
            </div>
          </div>
        </motion.div>
      </div>

      {/* Confidence Rating Buttons */}
      <div className="w-full space-y-2">
        <div className="text-[11px] font-mono text-white/60 text-center uppercase tracking-wider">
          Rate your recall accuracy:
        </div>
        <div className="grid grid-cols-3 gap-3">
          <button
            onClick={() => onRateConfidence("Confidence: Hard (Need revision)")}
            disabled={disabled}
            className="py-3 px-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 font-bold text-caption transition-all flex flex-col items-center gap-1 shadow-lg"
          >
            <span>🔴 Hard</span>
            <span className="text-[10px] text-red-300/70 font-normal">Review in 1 day</span>
          </button>
          <button
            onClick={() => onRateConfidence("Confidence: Medium (Good recall)")}
            disabled={disabled}
            className="py-3 px-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 font-bold text-caption transition-all flex flex-col items-center gap-1 shadow-lg"
          >
            <span>🟡 Good</span>
            <span className="text-[10px] text-amber-300/70 font-normal">Review in 3 days</span>
          </button>
          <button
            onClick={() => onRateConfidence("Confidence: Easy (Mastered)")}
            disabled={disabled}
            className="py-3 px-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 font-bold text-caption transition-all flex flex-col items-center gap-1 shadow-lg"
          >
            <span>🟢 Easy</span>
            <span className="text-[10px] text-emerald-300/70 font-normal">Review in 7 days</span>
          </button>
        </div>
      </div>
    </div>
  );
}
