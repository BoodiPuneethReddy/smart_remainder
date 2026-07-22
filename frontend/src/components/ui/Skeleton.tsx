/**
 * components/ui/Skeleton.tsx — Skeleton loading state system.
 *
 * Skeleton    — base shimmer primitive
 * Skeleton.Card     — matches Card.Default dimensions
 * Skeleton.StatCard — matches Card.Stat dimensions
 * Skeleton.TaskList — matches a list of Card.Task items
 * Skeleton.Chart    — matches a chart area
 *
 * Never use a bare spinner — use the appropriate skeleton.
 */
import React from 'react';
import { cn } from '@/lib/utils';

// ── Base shimmer primitive ────────────────────────────────────────────────────
interface SkeletonBaseProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: string;
}

function SkeletonBase({ className, width, height, rounded = 'rounded-input' }: SkeletonBaseProps) {
  return (
    <div
      className={cn('shimmer', rounded, className)}
      style={{ width, height: height ?? '16px' }}
      aria-hidden
    />
  );
}

// ── Skeleton.Card ──────────────────────────────────────────────────────────────
function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('glass rounded-card p-6 shadow-raised space-y-4', className)}>
      <div className="flex justify-between items-center">
        <SkeletonBase height={20} width="40%" />
        <SkeletonBase height={20} width={60} />
      </div>
      <SkeletonBase height={14} width="80%" />
      <SkeletonBase height={14} width="60%" />
      <SkeletonBase height={14} width="70%" />
    </div>
  );
}

// ── Skeleton.StatCard ──────────────────────────────────────────────────────────
function SkeletonStatCard({ className }: { className?: string }) {
  return (
    <div className={cn('glass rounded-card p-6 shadow-raised space-y-3', className)}>
      <SkeletonBase height={12} width={80} />
      <SkeletonBase height={36} width={100} />
      <SkeletonBase height={12} width={60} />
    </div>
  );
}

// ── Skeleton.TaskList ──────────────────────────────────────────────────────────
function SkeletonTaskList({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass rounded-card p-6 shadow-raised">
          <div className="flex items-start gap-4">
            {/* Priority ring placeholder */}
            <SkeletonBase height={64} width={64} rounded="rounded-full" className="flex-shrink-0" />
            <div className="flex-1 space-y-3">
              <SkeletonBase height={12} width="30%" />
              <SkeletonBase height={18} width="70%" />
              <SkeletonBase height={12} width="40%" />
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-[var(--card-border)] space-y-2">
            <SkeletonBase height={12} width="90%" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Skeleton.Chart ──────────────────────────────────────────────────────────────
function SkeletonChart({ className }: { className?: string }) {
  return (
    <div className={cn('glass rounded-card p-6 shadow-raised', className)}>
      <SkeletonBase height={20} width="30%" className="mb-6" />
      <div className="flex items-end gap-2 h-32">
        {[60, 80, 45, 90, 70, 55, 85].map((h, i) => (
          <div key={i} className="flex-1 shimmer rounded-t-input" style={{ height: `${h}%` }} />
        ))}
      </div>
      <div className="flex justify-between mt-3">
        {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
          <SkeletonBase key={d} height={10} width={24} />
        ))}
      </div>
    </div>
  );
}

// ── Export namespace ──────────────────────────────────────────────────────────
export const Skeleton = Object.assign(SkeletonBase, {
  Card: SkeletonCard,
  StatCard: SkeletonStatCard,
  TaskList: SkeletonTaskList,
  Chart: SkeletonChart,
});
