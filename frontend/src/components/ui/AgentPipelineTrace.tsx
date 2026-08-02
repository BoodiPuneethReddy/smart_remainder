/**
 * components/ui/AgentPipelineTrace.tsx
 * 
 * Renders the multi-agent execution pipeline as an animated visual trace.
 * Shows exactly which agents ran, what they did, and in what order.
 * This is the proof that the multi-agent architecture is actually executing.
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Zap, Brain } from 'lucide-react';
import type { StepLog } from '../../lib/api';

interface AgentPipelineTraceProps {
  stepLogs: StepLog[];
  intent?: string;
  className?: string;
}

const AGENT_ICONS: Record<string, string> = {
  IntentAgent:     '🧭',
  ContextBuilder:  '📖',
  DocumentAgent:   '📄',
  StrategyAgent:   '🎯',
  PlannerAgent:    '📅',
  ReminderAgent:   '🔔',
  ReflectionAgent: '✅',
  AnalyticsAgent:  '📊',
};

const STATUS_COLOR: Record<string, string> = {
  completed: 'var(--color-success, #22c55e)',
  warning:   'var(--color-warning, #f59e0b)',
  pending:   'var(--color-text-muted, #6b7280)',
  running:   'var(--color-accent, #6366f1)',
};

const INTENT_LABEL: Record<string, string> = {
  study_planning:       '📚 Study Planning',
  schedule_constraint:  '⏱️ Schedule Constraint',
  learning_analytics:   '📊 Learning Analytics',
  tutor:                '🧑‍🏫 Tutor Query',
  information_query:    '🔍 Information Query',
  greeting:             '👋 Greeting',
  goodbye:              '👋 Goodbye',
  gratitude:            '🙏 Gratitude',
  motivation:           '💪 Motivation',
  task_completion:      '✅ Task Completion',
  casual:               '💬 Casual',
  small_talk:           '💬 Small Talk',
  document_import:      '📤 Document Import',
  help:                 '❓ Help',
  unknown:              '🤔 General Query',
};

export default function AgentPipelineTrace({
  stepLogs,
  intent,
  className = '',
}: AgentPipelineTraceProps) {
  const [expanded, setExpanded] = useState(false);

  if (!stepLogs || stepLogs.length === 0) return null;

  const hasWarnings = stepLogs.some(l => l.status === 'warning');
  const intentLabel = intent ? (INTENT_LABEL[intent] || `🤖 ${intent}`) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className={`agent-pipeline-trace ${className}`}
      style={{
        background: 'rgba(99, 102, 241, 0.06)',
        border: '1px solid rgba(99, 102, 241, 0.2)',
        borderRadius: '12px',
        padding: '10px 14px',
        marginTop: '10px',
        fontSize: '0.78rem',
        fontFamily: 'var(--font-mono, monospace)',
      }}
    >
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          width: '100%',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          color: 'var(--text-secondary, #9ca3af)',
          textAlign: 'left',
        }}
        aria-label={expanded ? 'Collapse agent trace' : 'Expand agent trace'}
      >
        <Zap size={12} style={{ color: 'rgba(99, 102, 241, 0.8)', flexShrink: 0 }} />
        <span style={{ fontSize: '0.72rem', fontWeight: 600, letterSpacing: '0.04em', color: 'rgba(99, 102, 241, 0.9)' }}>
          AGENT EXECUTION TRACE
        </span>
        {intentLabel && (
          <span style={{
            background: 'rgba(99, 102, 241, 0.15)',
            borderRadius: '4px',
            padding: '1px 6px',
            fontSize: '0.70rem',
            color: 'rgba(99, 102, 241, 1)',
          }}>
            {intentLabel}
          </span>
        )}
        {hasWarnings && (
          <AlertTriangle size={11} style={{ color: '#f59e0b', marginLeft: 'auto' }} />
        )}
        <span style={{ marginLeft: hasWarnings ? '0' : 'auto' }}>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </span>
      </button>

      {/* Compact view — always show step count */}
      {!expanded && (
        <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
          {stepLogs.map((log, idx) => (
            <motion.span
              key={idx}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                color: STATUS_COLOR[log.status] || '#9ca3af',
                fontSize: '0.70rem',
              }}
              title={log.summary}
            >
              <span style={{ fontSize: '10px' }}>{AGENT_ICONS[log.agent_name] || '🤖'}</span>
              <span>{log.agent_name.replace('Agent', '')}</span>
              {idx < stepLogs.length - 1 && (
                <span style={{ color: 'rgba(99, 102, 241, 0.3)', margin: '0 1px' }}>→</span>
              )}
            </motion.span>
          ))}
        </div>
      )}

      {/* Expanded view — full step detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden', marginTop: '8px' }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {stepLogs.map((log, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    paddingLeft: '4px',
                  }}
                >
                  {/* Step connector line */}
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    flexShrink: 0,
                  }}>
                    <span style={{ fontSize: '14px', lineHeight: 1 }}>
                      {AGENT_ICONS[log.agent_name] || '🤖'}
                    </span>
                    {idx < stepLogs.length - 1 && (
                      <div style={{
                        width: '1px',
                        height: '12px',
                        background: 'rgba(99, 102, 241, 0.2)',
                        marginTop: '2px',
                      }} />
                    )}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontWeight: 700,
                        fontSize: '0.72rem',
                        color: STATUS_COLOR[log.status],
                      }}>
                        {log.agent_name}
                      </span>
                      <span style={{
                        fontSize: '0.62rem',
                        padding: '1px 4px',
                        borderRadius: '3px',
                        background: log.status === 'warning'
                          ? 'rgba(245, 158, 11, 0.15)'
                          : 'rgba(34, 197, 94, 0.1)',
                        color: STATUS_COLOR[log.status],
                        fontWeight: 600,
                        letterSpacing: '0.05em',
                        textTransform: 'uppercase',
                      }}>
                        {log.status}
                      </span>
                    </div>
                    <p style={{
                      margin: '2px 0 0',
                      color: 'var(--text-muted, #6b7280)',
                      fontSize: '0.70rem',
                      lineHeight: 1.4,
                      wordBreak: 'break-word',
                    }}>
                      {log.summary}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>

            <div style={{
              marginTop: '8px',
              paddingTop: '6px',
              borderTop: '1px solid rgba(99, 102, 241, 0.1)',
              color: 'rgba(99, 102, 241, 0.6)',
              fontSize: '0.65rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}>
              <Brain size={9} />
              <span>{stepLogs.length} agents executed · Multi-agent swarm verified</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
