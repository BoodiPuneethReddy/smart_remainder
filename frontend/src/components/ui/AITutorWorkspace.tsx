import React, { useState, useEffect, useRef } from 'react';
import { assessmentApi, QuizQuestion } from '../../lib/api';
import { 
  X, Brain, Award, Send, HelpCircle, FileText, ArrowRight, RefreshCw, 
  Clock, Bookmark, Sparkles, AlertCircle, BookOpen, CheckCircle, ChevronRight, User, Terminal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

import MCQOptionCards from '../tutor/formats/MCQOptionCards';
import TrueFalseToggle from '../tutor/formats/TrueFalseToggle';
import FillInBlankInput from '../tutor/formats/FillInBlankInput';
import ShortAnswerInput from '../tutor/formats/ShortAnswerInput';
import LongAnswerEssayEditor from '../tutor/formats/LongAnswerEssayEditor';
import FlashcardWorkspace from '../tutor/workspaces/FlashcardWorkspace';
import InterviewWorkspace from '../tutor/workspaces/InterviewWorkspace';
import ExplainMistakesWorkspace from '../tutor/workspaces/ExplainMistakesWorkspace';

// Get backend API client directly
import { apiClient } from '../../lib/api';

interface AITutorWorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
  subject: string;
  topic: string;
  documentId?: number;
  onSuccess?: () => void;
}

type ModeType = 'setup' | 'chat' | 'summary';

const PERSONALITIES = ["Socratic Tutor", "Professor", "Friendly Teacher", "Interviewer", "Exam Coach"];
const GOALS = ["College Exam", "Mid Exam", "Semester", "Placement", "GATE", "Interview", "General Learning"];
const MODES = ["Mixed", "Teach Me", "Test Me", "Revise", "Challenge Me", "Interview Me", "Explain Mistakes", "Flashcards"];
const FORMATS = ["Mixed", "Multiple Choice", "Short Answer", "True / False"];

const COGNITIVE_TIERS = [
  "Definition",
  "Concept",
  "Application",
  "Scenario",
  "Case Study",
  "Interview Question"
];

interface SourceChunk {
  document_name: string;
  page_number?: number;
  paragraph_number?: number;
  lecture_name?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  evaluation_confidence?: number;
  timestamp: string;
  sources?: SourceChunk[];
}

export default function AITutorWorkspace({
  isOpen,
  onClose,
  subject,
  topic,
  documentId,
  onSuccess,
}: AITutorWorkspaceProps) {
  const [workspaceMode, setWorkspaceMode] = useState<ModeType>('setup');
  
  // Setup Config
  const [personality, setPersonality] = useState("Socratic Tutor");
  const [goal, setGoal] = useState("General Learning");
  const [learningMode, setLearningMode] = useState("Mixed");
  const [formatType, setFormatType] = useState("Mixed");
  const [difficulty, setDifficulty] = useState(1);

  // Chat Log & Session
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
  const [studentInput, setStudentInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Active Turn Evaluation Metrics
  const [lastMetrics, setLastMetrics] = useState<{
    understanding: number;
    reasoning: number;
    application: number;
    confidence: number;
  } | null>(null);
  
  const [strengths, setStrengths] = useState<string[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [misconceptions, setMisconceptions] = useState<string[]>([]);
  const [polishedAnswer, setPolishedAnswer] = useState('');
  const [mermaidCode, setMermaidCode] = useState('');

  // Selected Text Highlighter Tooltip
  const [selectedText, setSelectedText] = useState('');
  const [selectionBox, setSelectionBox] = useState<{ x: number; y: number } | null>(null);

  // Timer
  const [timeTaken, setTimeTaken] = useState(0);
  const timerRef = useRef<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setWorkspaceMode('setup');
      setChatLog([]);
      setSessionId(null);
      setLastMetrics(null);
      setStrengths([]);
      setGaps([]);
      setMisconceptions([]);
      setPolishedAnswer('');
      setMermaidCode('');
    } else {
      stopTimer();
    }
    return () => stopTimer();
  }, [isOpen]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatLog]);

  const startTimer = () => {
    stopTimer();
    timerRef.current = window.setInterval(() => {
      setTimeTaken((t) => t + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const handleStartSession = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      const res = await apiClient.post('/api/assessment/tutor/start', {
        subject,
        topic,
        difficulty_level: difficulty,
        assessment_type: formatType.toLowerCase().replace(' ', '_'),
        target_goal: goal,
        teacher_personality: personality,
        learning_mode: learningMode,
        document_id: documentId
      });

      setSessionId(res.data.session_id);
      setDifficulty(res.data.difficulty_level);
      
      const firstMsg: ChatMessage = {
        id: 'first',
        role: 'assistant',
        content: res.data.first_question,
        evaluation_confidence: 100,
        timestamp: new Date().toISOString()
      };
      setChatLog([firstMsg]);
      setWorkspaceMode('chat');
      setTimeTaken(0);
      startTimer();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start AI Tutor workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendResponse = async (customText?: string) => {
    const textToSend = customText || studentInput;
    if (!textToSend.trim() || !sessionId) return;

    // Open-ended input validation (too short)
    if (textToSend.trim().length < 3) {
      alert("Please provide a more complete answer.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    
    // Optimistic student update
    const studentMsg: ChatMessage = {
      id: `student_${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    };
    setChatLog((prev) => [...prev, studentMsg]);
    if (!customText) setStudentInput('');

    try {
      const res = await apiClient.post('/api/assessment/tutor/respond', {
        session_id: sessionId,
        student_answer: textToSend,
        time_taken_seconds: timeTaken
      });

      if (res.data.status === 'SPEED_GUESS_DETECTED') {
        // Speed guess warning
        const warningMsg: ChatMessage = {
          id: `warn_${Date.now()}`,
          role: 'assistant',
          content: `⚠️ **Speed Protection Alert**: ${res.data.message}`,
          timestamp: new Date().toISOString()
        };
        setChatLog((prev) => [...prev, warningMsg]);
      } else {
        // Successful evaluation turn
        const tutorReply: ChatMessage = {
          id: `tutor_${Date.now()}`,
          role: 'assistant',
          content: res.data.explanation,
          evaluation_confidence: res.data.metrics?.confidence,
          timestamp: new Date().toISOString(),
          sources: res.data.sources
        };
        setChatLog((prev) => [...prev, tutorReply]);
        setDifficulty(res.data.difficulty_level);
        
        // Load evaluation scores
        setLastMetrics(res.data.metrics);
        setStrengths(res.data.strengths || []);
        setGaps(res.data.missing_points || []);
        setMisconceptions(res.data.misconceptions || []);
        setPolishedAnswer(res.data.better_exam_version || '');
        setMermaidCode(res.data.mermaid_code || '');
        
        // Reset timer for next question/turn
        setTimeTaken(0);
      }
    } catch (err: any) {
      setError('Connection interrupted. Please resubmit.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveStudyNote = async (text: string) => {
    try {
      await apiClient.post('/api/assessment/tutor/note', {
        subject,
        topic,
        content: text
      });
      alert('Saved to Study Notes handbook! ⭐');
    } catch (err) {
      alert('Failed to save study note.');
    }
  };

  // Text selection listener for Socratic Ask-Follow-up
  const handleTextSelection = (e: React.MouseEvent) => {
    const selection = window.getSelection();
    if (!selection) return;
    
    const selected = selection.toString().trim();
    if (selected.length > 3 && selected.length < 150) {
      setSelectedText(selected);
      // Position popover tooltip above cursor
      setSelectionBox({
        x: e.clientX,
        y: e.clientY - 40
      });
    } else {
      setSelectedText('');
      setSelectionBox(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto bg-black/75 backdrop-blur-md">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        className="relative w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden rounded-[24px] border border-white/10 bg-[#0B0E14]/90 text-white shadow-2xl backdrop-blur-xl"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20 text-orange-500">
              <Brain size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[var(--text-secondary)]">
                  {subject}
                </span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/20 text-orange-500">
                  {personality}
                </span>
              </div>
              <h2 className="text-body-lg font-bold text-white mt-1">Socratic Learning Studio: {topic}</h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-white/50 hover:text-white rounded-full hover:bg-white/5 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Dynamic Panels */}
        <div className="flex-1 overflow-hidden flex flex-col">
          
          {/* STEP 1: SETUP CONFIGURATION */}
          {workspaceMode === 'setup' && (
            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 max-w-4xl mx-auto w-full">
              <div className="text-center space-y-2">
                <Sparkles className="mx-auto text-orange-500" size={32} />
                <h3 className="text-h2 font-bold">Configure Socratic Study Session</h3>
                <p className="text-body-sm text-[var(--text-secondary)]">
                  Select your learning parameters. The AI tutor adjusts questions, depth, and tone to match your goal.
                </p>
              </div>

              {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-caption font-medium">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Personality */}
                <div className="space-y-2.5">
                  <label className="text-caption font-semibold text-[var(--text-secondary)] block">Tutor Personality</label>
                  <div className="grid grid-cols-2 gap-2">
                    {PERSONALITIES.map((p) => (
                      <button
                        key={p}
                        onClick={() => setPersonality(p)}
                        className={`p-3 text-left rounded-xl border text-caption font-medium transition-all ${
                          personality === p
                            ? 'border-orange-500 bg-orange-500/10 text-white font-bold shadow-[0_0_8px_rgba(239,110,38,0.15)]'
                            : 'border-white/5 bg-white/5 text-[var(--text-secondary)] hover:border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Goals */}
                <div className="space-y-2.5">
                  <label className="text-caption font-semibold text-[var(--text-secondary)] block">Study Focus / Target Goal</label>
                  <div className="grid grid-cols-2 gap-2">
                    {GOALS.map((g) => (
                      <button
                        key={g}
                        onClick={() => setGoal(g)}
                        className={`p-3 text-left rounded-xl border text-caption font-medium transition-all ${
                          goal === g
                            ? 'border-orange-500 bg-orange-500/10 text-white font-bold shadow-[0_0_8px_rgba(239,110,38,0.15)]'
                            : 'border-white/5 bg-white/5 text-[var(--text-secondary)] hover:border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Learning Mode */}
                <div className="space-y-2.5">
                  <label className="text-caption font-semibold text-[var(--text-secondary)] block">Learning Mode</label>
                  <div className="grid grid-cols-2 gap-2">
                    {MODES.map((m) => (
                      <button
                        key={m}
                        onClick={() => setLearningMode(m)}
                        className={`p-3 text-left rounded-xl border text-caption font-medium transition-all ${
                          learningMode === m
                            ? 'border-orange-500 bg-orange-500/10 text-white font-bold shadow-[0_0_8px_rgba(239,110,38,0.15)]'
                            : 'border-white/5 bg-white/5 text-[var(--text-secondary)] hover:border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Format Type */}
                <div className="space-y-2.5">
                  <label className="text-caption font-semibold text-[var(--text-secondary)] block">Assessment Format</label>
                  <div className="grid grid-cols-2 gap-2">
                    {FORMATS.map((f) => (
                      <button
                        key={f}
                        onClick={() => setFormatType(f)}
                        className={`p-3 text-left rounded-xl border text-caption font-medium transition-all ${
                          formatType === f
                            ? 'border-orange-500 bg-orange-500/10 text-white font-bold shadow-[0_0_8px_rgba(239,110,38,0.15)]'
                            : 'border-white/5 bg-white/5 text-[var(--text-secondary)] hover:border-white/10 hover:bg-white/10'
                        }`}
                      >
                        {f}
                      </button>
                    ))}
                  </div>
                </div>

              </div>

              {/* Action */}
              <div className="pt-6 text-center">
                <button
                  onClick={handleStartSession}
                  disabled={isSubmitting}
                  className="px-8 py-3.5 bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:brightness-110 rounded-xl font-semibold text-caption transition-all inline-flex items-center gap-2 shadow-lg shadow-orange-500/20 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="animate-spin" size={16} /> Initializing Tutor...
                    </>
                  ) : (
                    <>
                      Enter Learning Workspace <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: ACTIVE SOCRATIC CHAT WORKSPACE */}
          {workspaceMode === 'chat' && (
            <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
              
              {/* Left Chat Column */}
              <div className="flex-1 flex flex-col border-r border-white/10 overflow-hidden">
                
                {/* Cognitive Tier Path tracker */}
                <div className="px-6 py-3 bg-white/5 border-b border-white/5 flex items-center gap-2 overflow-x-auto text-[11px] font-mono">
                  {COGNITIVE_TIERS.map((tier, idx) => {
                    const isCurrent = difficulty === idx + 1;
                    const isPassed = difficulty > idx + 1;
                    return (
                      <React.Fragment key={tier}>
                        {idx > 0 && <ChevronRight size={12} className="text-white/20 shrink-0" />}
                        <span className={`px-2.5 py-0.5 rounded-full shrink-0 font-medium ${
                          isCurrent 
                            ? 'bg-orange-500 text-white font-bold shadow-sm'
                            : isPassed 
                            ? 'text-emerald-400 font-bold'
                            : 'text-white/40'
                        }`}>
                          {tier}
                        </span>
                      </React.Fragment>
                    );
                  })}
                </div>

                {/* Chat Message Logs */}
                <div 
                  className="flex-1 overflow-y-auto p-6 space-y-6 relative"
                  onMouseUp={handleTextSelection}
                >
                  {chatLog.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500 shrink-0">
                          <Brain size={16} />
                        </div>
                      )}
                      
                      <div className="relative group max-w-[80%]">
                        <div className={`p-4 rounded-2xl border text-body-sm leading-relaxed ${
                          msg.role === 'user'
                            ? 'bg-orange-500/10 border-orange-500/20 text-white rounded-tr-none'
                            : 'bg-white/5 border-white/5 text-[var(--text-primary)] rounded-tl-none'
                        }`}>
                          {msg.content}

                          {msg.evaluation_confidence && msg.role === 'assistant' && (
                            <div className="text-[10px] text-white/40 mt-2 font-mono flex items-center gap-1">
                              <CheckCircle size={10} className="text-emerald-400" />
                              Evaluation Grounding: {msg.evaluation_confidence}%
                            </div>
                          )}

                          {msg.sources && msg.sources.length > 0 && msg.role === 'assistant' && (
                            <div className="mt-2 pt-2 border-t border-white/5 space-y-1 text-[10px] font-mono text-white/60">
                              <span className="text-[9px] uppercase tracking-wider text-orange-400 font-bold block">Retrieved Citation Sources:</span>
                              {msg.sources.map((s, idx) => (
                                <div key={idx} className="flex items-center gap-1.5 bg-white/5 px-2 py-0.5 rounded text-[10px]">
                                  <FileText size={10} className="text-orange-400 shrink-0" />
                                  <span>
                                    [{s.lecture_name || 'Lecture 3'}] {s.document_name}, Page {s.page_number || 1}, Para {s.paragraph_number || 1}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Save to Study Notes Button */}
                        {msg.role === 'assistant' && (
                          <button
                            onClick={() => handleSaveStudyNote(msg.content)}
                            className="absolute -right-8 top-2 p-1.5 rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Save to Study Notes"
                          >
                            <Bookmark size={12} />
                          </button>
                        )}
                      </div>

                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/50 shrink-0">
                          <User size={16} />
                        </div>
                      )}
                    </div>
                  ))}

                  {isSubmitting && (
                    <div className="flex gap-4 justify-start">
                      <div className="w-8 h-8 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-500 shrink-0">
                        <Brain size={16} />
                      </div>
                      <div className="p-4 rounded-2xl border border-white/5 bg-white/5 text-body-sm text-[var(--text-secondary)] italic rounded-tl-none flex items-center gap-2">
                        <span className="w-3.5 h-3.5 border-t border-orange-500 rounded-full animate-spin" />
                        AI Tutor processing evaluation...
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />

                  {/* Highlighting Follow-Up floating tooltip */}
                  <AnimatePresence>
                    {selectionBox && selectedText && (
                      <motion.button
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        style={{
                          position: 'fixed',
                          left: selectionBox.x,
                          top: selectionBox.y,
                        }}
                        onClick={() => {
                          const customQuery = `Explain more about: "${selectedText}"`;
                          handleSendResponse(customQuery);
                          setSelectedText('');
                          setSelectionBox(null);
                        }}
                        className="px-3 py-1.5 bg-orange-500 text-white font-bold text-caption rounded-lg flex items-center gap-1.5 shadow-lg border border-orange-400 z-50 hover:brightness-110"
                      >
                        <HelpCircle size={12} /> Ask Tutor about this
                      </motion.button>
                    )}
                  </AnimatePresence>
                </div>

                {/* Socratic Scaffolding Prompt chips */}
                <div className="px-6 py-2 border-t border-white/5 flex gap-2 overflow-x-auto scrollbar-none shrink-0 bg-white/2">
                  <button
                    onClick={() => handleSendResponse("Can you explain that simply?")}
                    className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white text-caption shrink-0"
                  >
                    Explain simply
                  </button>
                  <button
                    onClick={() => handleSendResponse("Give me a concrete example.")}
                    className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white text-caption shrink-0"
                  >
                    Give an example
                  </button>
                  <button
                    onClick={() => handleSendResponse("Explain like I'm 10.")}
                    className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white text-caption shrink-0"
                  >
                    Explain like I'm 10
                  </button>
                  <button
                    onClick={() => handleSendResponse("I think my answer was correct. Can you verify against references?")}
                    className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 hover:text-white text-caption shrink-0"
                  >
                    Challenge grading
                  </button>
                </div>

                {/* Bottom Dynamic Input Area based on Format & Mode */}
                <div className="p-4 border-t border-white/10 bg-white/5 shrink-0">
                  {learningMode === "Flashcards" ? (
                    <FlashcardWorkspace
                      topic={topic}
                      question={chatLog[chatLog.length - 1]?.content || ""}
                      answer={chatLog[chatLog.length - 1]?.content || ""}
                      onRateConfidence={(rating) => handleSendResponse(rating)}
                      disabled={isSubmitting}
                    />
                  ) : learningMode === "Interview Me" ? (
                    <InterviewWorkspace
                      topic={topic}
                      personality={personality}
                      scenarioText={chatLog[0]?.content || ""}
                      onSubmitCandidateAnswer={(ans) => handleSendResponse(ans)}
                      mermaidCode={mermaidCode}
                      disabled={isSubmitting}
                    />
                  ) : learningMode === "Explain Mistakes" ? (
                    <ExplainMistakesWorkspace
                      topic={topic}
                      misconceptionText={misconceptions[0]}
                      onSubmitRemediation={(ans) => handleSendResponse(ans)}
                      disabled={isSubmitting}
                    />
                  ) : formatType === "Multiple Choice" ? (
                    <MCQOptionCards
                      onSelectOption={(opt) => handleSendResponse(opt)}
                      disabled={isSubmitting}
                    />
                  ) : formatType === "True / False" ? (
                    <TrueFalseToggle
                      onSelectChoice={(choice) => handleSendResponse(choice)}
                      disabled={isSubmitting}
                    />
                  ) : formatType === "Fill in the Blanks" ? (
                    <FillInBlankInput
                      onSubmitBlank={(text) => handleSendResponse(text)}
                      disabled={isSubmitting}
                    />
                  ) : formatType === "Long Answer" ? (
                    <LongAnswerEssayEditor
                      onSubmitEssay={(essay) => handleSendResponse(essay)}
                      disabled={isSubmitting}
                    />
                  ) : (
                    <ShortAnswerInput
                      onSubmitShortAnswer={(ans) => handleSendResponse(ans)}
                      disabled={isSubmitting}
                    />
                  )}
                </div>

              </div>

              {/* Right Evaluation & Whiteboard Sidebar Column */}
              <div className="w-full md:w-80 overflow-y-auto bg-white/2 p-6 flex flex-col gap-6">
                
                {/* 1. Evaluation Score Dials */}
                <div>
                  <h4 className="text-caption font-bold text-white uppercase tracking-wider mb-3">Tutor Evaluation Metrics</h4>
                  {lastMetrics ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-center">
                        <span className="text-[10px] text-white/40 block">Understanding</span>
                        <span className="text-body-lg font-bold text-orange-500">{lastMetrics.understanding}%</span>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-center">
                        <span className="text-[10px] text-white/40 block">Reasoning</span>
                        <span className="text-body-lg font-bold text-amber-500">{lastMetrics.reasoning}%</span>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-center">
                        <span className="text-[10px] text-white/40 block">Application</span>
                        <span className="text-body-lg font-bold text-emerald-500">{lastMetrics.application}%</span>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-center">
                        <span className="text-[10px] text-white/40 block">Grounding</span>
                        <span className="text-body-lg font-bold text-blue-500">{lastMetrics.confidence}%</span>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl border border-white/5 bg-white/5 text-center text-caption text-white/40 italic">
                      Submit an answer to see cognitive feedback.
                    </div>
                  )}
                </div>

                {/* 2. Concept Gaps & Misconceptions */}
                {(strengths.length > 0 || gaps.length > 0 || misconceptions.length > 0) && (
                  <div className="space-y-4">
                    
                    {strengths.length > 0 && (
                      <div>
                        <span className="text-[10px] font-bold text-emerald-400 uppercase block mb-1.5">Strengths</span>
                        <ul className="space-y-1 text-caption text-white/70 list-disc pl-4">
                          {strengths.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    )}

                    {gaps.length > 0 && (
                      <div>
                        <span className="text-[10px] font-bold text-orange-400 uppercase block mb-1.5">Missing Concept Gaps</span>
                        <ul className="space-y-1 text-caption text-white/70 list-disc pl-4">
                          {gaps.map((g, i) => <li key={i}>{g}</li>)}
                        </ul>
                      </div>
                    )}

                    {misconceptions.length > 0 && (
                      <div className="p-3 rounded-lg border border-red-500/20 bg-red-500/10">
                        <span className="text-[10px] font-bold text-red-400 uppercase block mb-1">Misconception Detected ⚠</span>
                        <ul className="space-y-1 text-[11px] text-red-300 list-disc pl-4">
                          {misconceptions.map((m, i) => <li key={i}>{m}</li>)}
                        </ul>
                      </div>
                    )}

                  </div>
                )}

                {/* 3. Polish Sandbox Comparison */}
                {polishedAnswer && (
                  <div className="p-4 rounded-xl bg-orange-500/5 border border-orange-500/20 space-y-2">
                    <span className="text-[10px] font-bold text-orange-500 uppercase tracking-wider block">Answer Polish Sandbox</span>
                    <p className="text-caption text-orange-200/90 italic leading-relaxed">
                      "{polishedAnswer}"
                    </p>
                    <div className="text-[9px] text-white/40 flex flex-wrap gap-2">
                      <span className="text-emerald-400">🟢 Technical terms expanded</span>
                      <span className="text-emerald-400">🟢 Structure polished</span>
                    </div>
                  </div>
                )}

                {/* 4. Whiteboard diagram renderer */}
                {mermaidCode && (
                  <div className="p-4 rounded-xl border border-white/5 bg-white/5 space-y-2">
                    <span className="text-[10px] font-bold text-white uppercase tracking-wider block flex items-center gap-1.5">
                      <Terminal size={12} className="text-orange-500" />
                      Whiteboard Diagram
                    </span>
                    <pre className="p-3 rounded bg-black/40 text-[10px] font-mono text-emerald-400 overflow-x-auto leading-relaxed border border-white/5">
                      {mermaidCode}
                    </pre>
                  </div>
                )}

              </div>

            </div>
          )}

        </div>
      </motion.div>
    </div>
  );
}
