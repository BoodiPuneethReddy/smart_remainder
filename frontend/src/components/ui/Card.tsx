/**
 * components/ui/Card.tsx — Card variant system.
 *
 * Variants:
 *   Card.Default  — glassmorphic container (dashboard cards, modals)
 *   Card.Stat     — large number + label + optional trend
 *   Card.Task     — priority-score hero (radial score, hover breakdown, explanation)
 *   Card.Empty    — empty state (icon + message + CTA)
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getPriorityColor, getPriorityLabel, getPriorityTier, type PriorityTier } from '@/lib/design-tokens';
import { liftOnHover, staggerChild } from '@/lib/motion';
import { Button } from './Button';

// ── Card.Default ─────────────────────────────────────────────────────────────
interface CardDefaultProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  interactive?: boolean;
  noPadding?: boolean;
}

function CardDefault({ children, className, style, interactive = false, noPadding = false }: CardDefaultProps) {
  return (
    <motion.div
      variants={interactive ? liftOnHover : undefined}
      initial={interactive ? 'rest' : undefined}
      whileHover={interactive ? 'hover' : undefined}
      style={style}
      className={cn(
        'glass rounded-card',
        'shadow-raised',
        interactive && 'cursor-pointer transition-shadow duration-150 hover:shadow-raised-hover',
        !noPadding && 'p-6',
        className,
      )}
    >
      {children}
    </motion.div>
  );
}

// ── Card.Stat ─────────────────────────────────────────────────────────────────
interface CardStatProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  icon?: React.ReactNode;
  accentColor?: string;
  className?: string;
}

function CardStat({ label, value, unit, trend, trendValue, icon, accentColor, className }: CardStatProps) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-[var(--success)]' : trend === 'down' ? 'text-[var(--danger)]' : 'text-[var(--text-muted)]';

  return (
    <motion.div
      variants={liftOnHover}
      initial="rest"
      whileHover="hover"
      className={cn(
        'glass rounded-card p-6 shadow-raised transition-shadow duration-150 hover:shadow-raised-hover',
        className,
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-caption text-[var(--text-secondary)] uppercase tracking-wider">{label}</p>
        {icon && (
          <span style={{ color: accentColor || 'var(--info)' }} className="opacity-80">
            {icon}
          </span>
        )}
      </div>

      <div className="flex items-end gap-1">
        <span className="text-display font-bold" style={{ color: accentColor || 'var(--text-primary)' }}>
          {value}
        </span>
        {unit && <span className="text-body-sm text-[var(--text-secondary)] mb-1">{unit}</span>}
      </div>

      {trend && trendValue && (
        <div className={cn('flex items-center gap-1 mt-2 text-caption', trendColor)}>
          <TrendIcon size={12} />
          <span>{trendValue}</span>
        </div>
      )}
    </motion.div>
  );
}

// ── PriorityRing (used inside Card.Task) ─────────────────────────────────────
interface PriorityRingProps {
  score: number;
  size?: number;
}

function PriorityRing({ score, size = 64 }: PriorityRingProps) {
  const color = getPriorityColor(score);
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={5}
        />
        {/* Progress */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      {/* Score number */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-caption font-bold" style={{ color, fontSize: size < 56 ? 10 : 12 }}>
          {Math.round(score)}
        </span>
      </div>
    </div>
  );
}

// ── ScoreBar (sub-score breakdown shown on hover) ─────────────────────────────
function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-caption text-[var(--text-secondary)] w-20 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/8 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(value / 10) * 100}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
      <span className="text-caption w-5 text-right" style={{ color }}>{value.toFixed(1)}</span>
    </div>
  );
}

// ── Card.Task ─────────────────────────────────────────────────────────────────
interface CardTaskProps {
  title: string;
  subject: string;
  taskType: string;
  dueDate: string;
  priorityScore: number;
  urgencyScore: number;
  importanceScore: number;
  weaknessScore: number;
  effortScore: number;
  aiExplanation: string;
  isCompleted?: boolean;
  onComplete?: () => void;
  onDelete?: () => void;
  className?: string;
}

function CardTask({
  title, subject, taskType, dueDate,
  priorityScore, urgencyScore, importanceScore, weaknessScore, effortScore,
  aiExplanation, isCompleted = false, onComplete, onDelete, className,
}: CardTaskProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [completing, setCompleting] = useState(false);
  const color = getPriorityColor(priorityScore);
  const tier = getPriorityTier(priorityScore);
  const tierLabel = getPriorityLabel(priorityScore);
  const daysLeft = Math.ceil((new Date(dueDate).getTime() - Date.now()) / 86400000);

  const subScores = [
    { label: 'Urgency', value: urgencyScore, color: 'var(--priority-high)' },
    { label: 'Importance', value: importanceScore, color: 'var(--info)' },
    { label: 'Weakness', value: weaknessScore, color: 'var(--priority-medium)' },
    { label: 'Effort', value: effortScore, color: 'var(--priority-low)' },
  ];

  const handleComplete = async () => {
    if (completing || isCompleted) return;
    setCompleting(true);
    await onComplete?.();
    setCompleting(false);
  };

  return (
    <motion.div
      variants={staggerChild}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn(
        'glass rounded-card p-6 shadow-raised',
        'transition-all duration-150',
        'hover:shadow-raised-hover hover:bg-[var(--card-hover)]',
        isCompleted && 'opacity-50',
        className,
      )}
      style={{ transform: isHovered ? 'translateY(-2px)' : 'translateY(0)' }}
    >
      {/* Header row */}
      <div className="flex items-start gap-4">
        {/* Priority ring — the visual hero */}
        <PriorityRing score={priorityScore} size={64} />

        <div className="flex-1 min-w-0">
          {/* Subject + type badges */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className="text-caption px-2 py-0.5 rounded-badge font-medium"
              style={{ backgroundColor: `${color}22`, color }}
            >
              {tierLabel} Priority
            </span>
            <span className="text-caption text-[var(--text-secondary)] px-2 py-0.5 rounded-badge border border-[var(--card-border)]">
              {taskType.charAt(0).toUpperCase() + taskType.slice(1)}
            </span>
          </div>

          {/* Title */}
          <h3
            className={cn('text-h3 text-[var(--text-primary)] truncate', isCompleted && 'line-through')}
            title={title}
          >
            {title}
          </h3>

          {/* Subject + due date */}
          <p className="text-body-sm text-[var(--text-secondary)] mt-0.5">
            {subject} ·{' '}
            <span style={{ color: daysLeft <= 1 ? 'var(--danger)' : daysLeft <= 3 ? 'var(--warning)' : 'var(--text-secondary)' }}>
              {daysLeft <= 0 ? 'Due today' : daysLeft === 1 ? 'Due tomorrow' : `Due in ${daysLeft}d`}
            </span>
          </p>
        </div>

        {/* Actions */}
        {!isCompleted && (
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={handleComplete}
              title="Mark complete"
              className={cn(
                'w-8 h-8 rounded-full border-2 flex items-center justify-center',
                'transition-all duration-150 hover:scale-110',
                'border-[var(--card-border)] hover:border-[var(--success)]',
              )}
            >
              <AnimatePresence>
                {completing && (
                  <motion.svg
                    key="check"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: [0, 1.2, 1], opacity: 1 }}
                    transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
                    viewBox="0 0 16 16" fill="none"
                    className="w-4 h-4 text-[var(--success)]"
                    stroke="currentColor" strokeWidth={2.5}
                  >
                    <path d="M3 8l3.5 3.5L13 4.5" strokeLinecap="round" strokeLinejoin="round" />
                  </motion.svg>
                )}
              </AnimatePresence>
            </button>
          </div>
        )}
      </div>

      {/* AI explanation — always visible, directly below score */}
      {aiExplanation && (
        <p className="text-body-sm text-[var(--text-secondary)] mt-3 leading-relaxed border-t border-[var(--card-border)] pt-3">
          {aiExplanation}
        </p>
      )}

      {/* Sub-score breakdown — revealed on hover */}
      <AnimatePresence>
        {isHovered && !isCompleted && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-4 pt-3 border-t border-[var(--card-border)] space-y-2">
              <p className="text-caption text-[var(--text-muted)] mb-2 uppercase tracking-wider">AI Reasoning</p>
              {subScores.map((s) => (
                <ScoreBar key={s.label} {...s} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Card.Empty ─────────────────────────────────────────────────────────────────
interface CardEmptyProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

function CardEmpty({ icon, title, description, action, className }: CardEmptyProps) {
  return (
    <div className={cn(
      'glass rounded-card p-12 flex flex-col items-center justify-center text-center',
      'border-dashed border-[var(--card-border)]',
      className,
    )}>
      <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
           style={{ background: 'var(--surface-hover)' }}>
        <span className="text-[var(--text-muted)]">{icon}</span>
      </div>
      <h3 className="text-h3 text-[var(--text-primary)] mb-2">{title}</h3>
      <p className="text-body-sm text-[var(--text-secondary)] max-w-xs leading-relaxed">{description}</p>
      {action && (
        <Button variant="primary" className="mt-6" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}

// ── Export namespace ──────────────────────────────────────────────────────────
export const Card = {
  Default: CardDefault,
  Stat: CardStat,
  Task: CardTask,
  Empty: CardEmpty,
};
