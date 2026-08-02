/**
 * pages/AIPlanner.tsx — AI Planner page.
 * Left: daily study plan with time allocation.
 * Right: AI chat Q&A assistant with Agent Pipeline Trace.
 */
import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Brain, MessageSquare, Clock, Lightbulb, Sparkles, Paperclip } from 'lucide-react';
import { plannerApi, chatApi, StepLog } from '@/lib/api';
import {
  Card, Button, Input, Skeleton, iconSize,
} from '@/components/ui';
import { PriorityBadge } from '@/components/ui';
import { fadeSlideIn, staggerContainer, staggerChild, springIn } from '@/lib/motion';
import { formatDuration } from '@/lib/utils';
import { getPriorityColor } from '@/lib/design-tokens';
import { format } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';
import ImportModal from '@/components/ui/ImportModal';
import AgentPipelineTrace from '@/components/ui/AgentPipelineTrace';

// ── Chat message bubble ────────────────────────────────────────────────────────
function ChatBubble({
  role, text, time, stepLogs, intent
}: {
  role: 'user' | 'ai';
  text: string;
  time?: string;
  stepLogs?: StepLog[];
  intent?: string;
}) {
  return (
    <motion.div
      variants={springIn}
      initial="initial"
      animate="animate"
      className={`flex flex-col ${role === 'user' ? 'items-end' : 'items-start'}`}
    >
      <div className={`max-w-[85%] rounded-card px-4 py-3 ${
        role === 'user'
          ? 'bg-[var(--info)] text-white ml-8'
          : 'glass text-[var(--text-primary)] mr-4'
      }`}>
        {role === 'ai' && (
          <div className="flex items-center gap-1.5 mb-1.5">
            <Sparkles size={12} style={{ color: 'var(--priority-medium)' }} />
            <span className="text-caption font-medium" style={{ color: 'var(--priority-medium)' }}>AI Study OS</span>
            {intent && (
              <span style={{
                fontSize: '0.60rem',
                padding: '1px 5px',
                borderRadius: '4px',
                background: 'rgba(99,102,241,0.15)',
                color: 'rgba(99,102,241,0.9)',
                fontWeight: 600,
              }}>
                {intent.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        )}
        <p className="text-body-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        {time && <p className="text-[11px] opacity-50 mt-1">{time}</p>}
      </div>
      {role === 'ai' && stepLogs && stepLogs.length > 0 && (
        <div className="mr-4 w-full max-w-[85%]">
          <AgentPipelineTrace stepLogs={stepLogs} intent={intent} />
        </div>
      )}
    </motion.div>
  );
}

// ── Suggestion chips ──────────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What should I study today?",
  "Which subject needs the most attention?",
  "How can I improve my completion rate?",
  "Create a study schedule for this week",
];

export default function AIPlanner() {
  const qc = useQueryClient();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Array<{
    role: 'user' | 'ai';
    text: string;
    time: string;
    stepLogs?: StepLog[];
    intent?: string;
  }>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatFileInputRef = useRef<HTMLInputElement>(null);
  const [chatFile, setChatFile] = useState<File | null>(null);
  const [showImport, setShowImport] = useState(false);

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ['planner', 'daily'],
    queryFn: () => plannerApi.daily().then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: history } = useQuery({
    queryKey: ['chat', 'history'],
    queryFn: () => chatApi.history().then((r) => r.data),
    staleTime: 60_000,
  });

  // Load history into messages once
  useEffect(() => {
    if (history && messages.length === 0) {
      const msgs = history.slice(-10).flatMap((h) => [
        { role: 'user' as const, text: h.question, time: format(new Date(h.created_at), 'h:mm a') },
        { role: 'ai' as const, text: h.answer, time: format(new Date(h.created_at), 'h:mm a') },
      ]);
      setMessages(msgs);
    }
  }, [history]);

  const { mutate: askQuestion, isPending: asking } = useMutation({
    mutationFn: (q: string) => chatApi.ask(q).then((r) => r.data),
    onSuccess: (data) => {
      const time = format(new Date(), 'h:mm a');
      setMessages((prev) => [...prev, {
        role: 'ai',
        text: data.answer,
        time,
        stepLogs: data.step_logs,
        intent: data.primary_intent,
      }]);
    },
  });

  const handleSend = () => {
    if (!question.trim() || asking) return;
    const q = question.trim();
    const time = format(new Date(), 'h:mm a');
    setMessages((prev) => [...prev, { role: 'user', text: q, time }]);
    setQuestion('');
    askQuestion(q);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <motion.div variants={fadeSlideIn} initial="initial" animate="animate"
                className="page-padding space-y-6 max-w-7xl">
      <div>
        <h1 className="text-h1 text-[var(--text-primary)]">AI Study Planner</h1>
        <p className="text-body-sm text-[var(--text-secondary)] mt-1">
          Today's personalized study plan + AI coaching assistant
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        {/* ── Left: Daily Study Plan ──────────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Clock size={iconSize.button} style={{ color: 'var(--info)' }} />
            <h2 className="text-h2 text-[var(--text-primary)]">Today's Schedule</h2>
          </div>

          {planLoading ? (
            <Skeleton.TaskList count={3} />
          ) : (plan?.tasks ?? []).length === 0 ? (
            <Card.Empty
              icon={<Brain size={iconSize.feature} />}
              title="Nothing to plan today"
              description="Add tasks to get an AI-generated study schedule with time allocation."
              action={{ label: 'Add Tasks', onClick: () => window.location.href = '/tasks' }}
            />
          ) : (
            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
              {(plan?.tasks ?? []).map((task, i) => {
                const color = getPriorityColor(task.priority_score);
                const daysLeft = Math.ceil((new Date(task.due_date).getTime() - Date.now()) / 86400000);
                return (
                  <motion.div key={task.task_id} variants={staggerChild}>
                    <Card.Default interactive className="relative overflow-hidden">
                      {/* Accent left border */}
                      <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-card" style={{ background: color }} />
                      <div className="pl-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <PriorityBadge score={task.priority_score} />
                              <span className="text-caption text-[var(--text-secondary)]">
                                {task.subject} · {daysLeft <= 0 ? 'Due today' : `${daysLeft}d left`}
                              </span>
                            </div>
                            <h3 className="text-h3 text-[var(--text-primary)] truncate">{task.title}</h3>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="text-display font-bold" style={{ color, fontSize: '24px' }}>
                              {task.recommended_minutes}m
                            </p>
                            <p className="text-caption text-[var(--text-secondary)]">study time</p>
                          </div>
                        </div>
                        <p className="text-body-sm text-[var(--text-secondary)] mt-2 leading-relaxed">
                          {task.ai_explanation}
                        </p>
                      </div>
                    </Card.Default>
                  </motion.div>
                );
              })}
              <Card.Default className="text-center py-3">
                <p className="text-body-sm text-[var(--text-secondary)]">
                  Total recommended:{' '}
                  <span className="text-[var(--info)] font-semibold">
                    {formatDuration(plan?.total_recommended_minutes ?? 0)}
                  </span>{' '}
                  of focused study
                </p>
              </Card.Default>
            </motion.div>
          )}
        </div>

        {/* ── Right: AI Chat ────────────────────────────────────────────────── */}
        <Card.Default noPadding className="flex flex-col" style={{ height: '600px' } as any}>
          {/* Chat header */}
          <div className="flex items-center gap-3 p-4 border-b border-[var(--card-border)]">
            <div className="w-8 h-8 rounded-full flex items-center justify-center"
                 style={{ background: 'linear-gradient(135deg, var(--priority-medium), var(--info))' }}>
              <Brain size={16} className="text-white" />
            </div>
            <div>
              <p className="text-h3 text-[var(--text-primary)]">AI Study Coach</p>
              <p className="text-caption text-[var(--success)]">● Online · Powered by AMD</p>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <MessageSquare size={iconSize.feature} className="text-[var(--text-muted)]" />
                <div>
                  <p className="text-h3 text-[var(--text-primary)] mb-1">Ask your AI coach</p>
                  <p className="text-body-sm text-[var(--text-secondary)]">
                    Try asking: "What should I study today?"
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setQuestion(s)}
                      className="text-caption px-3 py-1.5 rounded-full border border-[var(--card-border)] text-[var(--text-secondary)] hover:border-[var(--info)] hover:text-[var(--info)] transition-all duration-150"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <ChatBubble
                key={i}
                role={m.role}
                text={m.text}
                time={m.time}
                stepLogs={m.stepLogs}
                intent={m.intent}
              />
            ))}
            {asking && (
              <motion.div variants={springIn} initial="initial" animate="animate" className="flex justify-start">
                <div className="glass rounded-card px-4 py-3">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.div key={i} className="w-2 h-2 rounded-full bg-[var(--text-muted)]"
                                  animate={{ opacity: [0.3, 1, 0.3] }}
                                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }} />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-[var(--card-border)]">
            <div className="flex gap-2">
              <input
                type="file"
                ref={chatFileInputRef}
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    setChatFile(e.target.files[0]);
                    setShowImport(true);
                  }
                }}
                accept=".pdf,.jpg,.jpeg,.png"
                style={{ display: 'none' }}
              />
              <Button
                variant="secondary"
                onClick={() => chatFileInputRef.current?.click()}
                icon={<Paperclip size={iconSize.inline} />}
              />
              <Input
                placeholder="Ask about your study plan..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                className="flex-1"
              />
              <Button variant="primary" onClick={handleSend} loading={asking} icon={<Send size={iconSize.inline} />} />
            </div>
          </div>
        </Card.Default>
      </div>

      {/* Import Modal */}
      <ImportModal
        isOpen={showImport}
        onClose={() => {
          setShowImport(false);
          setChatFile(null);
          if (chatFileInputRef.current) chatFileInputRef.current.value = '';
        }}
        initialFile={chatFile}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ['planner'] });
          qc.invalidateQueries({ queryKey: ['tasks'] });
          qc.invalidateQueries({ queryKey: ['analytics'] });
        }}
      />
    </motion.div>
  );
}
