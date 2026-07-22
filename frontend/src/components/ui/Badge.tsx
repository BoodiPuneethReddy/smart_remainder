/**
 * components/ui/Badge.tsx — Priority and status badges.
 * Icon sizing constants — 16/20/24px scale, Lucide only.
 */
import React from 'react';
import { cn } from '@/lib/utils';
import { getPriorityColor, getPriorityLabel } from '@/lib/design-tokens';

// ── Badge ─────────────────────────────────────────────────────────────────────
interface BadgeProps {
  children: React.ReactNode;
  color?: string;
  className?: string;
  size?: 'sm' | 'md';
}

export function Badge({ children, color, className, size = 'md' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-badge',
        size === 'sm' ? 'text-[11px] px-1.5 py-0.5' : 'text-caption px-2 py-0.5',
        className,
      )}
      style={color ? { backgroundColor: `${color}22`, color } : undefined}
    >
      {children}
    </span>
  );
}

// ── Priority badge ─────────────────────────────────────────────────────────────
export function PriorityBadge({ score }: { score: number }) {
  const color = getPriorityColor(score);
  const label = getPriorityLabel(score);
  return <Badge color={color}>{label}</Badge>;
}

// ── Task type badge ───────────────────────────────────────────────────────────
const typeColors: Record<string, string> = {
  exam:       'var(--priority-high)',
  project:    'var(--priority-medium)',
  assignment: 'var(--info)',
  quiz:       'var(--priority-medium)',
  homework:   'var(--priority-low)',
  reading:    'var(--text-secondary)',
};

export function TaskTypeBadge({ type }: { type: string }) {
  const color = typeColors[type] ?? 'var(--text-secondary)';
  return <Badge color={color}>{type.charAt(0).toUpperCase() + type.slice(1)}</Badge>;
}

// ── Icon sizing constants — import these everywhere, never hardcode px ────────
export const iconSize = {
  inline: 16,   // inside text, inputs
  button: 20,   // buttons, nav items
  feature: 24,  // empty states, callouts
} as const;
