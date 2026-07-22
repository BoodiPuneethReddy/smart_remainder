/**
 * components/ui/ChartTheme.tsx — Shared Recharts configuration.
 * Every chart imports chartDefaults and uses these props.
 * Never repeat axis/tooltip/grid config per chart.
 */
import React from 'react';
import { Tooltip, Legend } from 'recharts';
import { chartTheme } from '@/lib/design-tokens';

// ── Shared axis props ─────────────────────────────────────────────────────────
export const axisProps = {
  tick: {
    fill: chartTheme.axisColor,
    fontSize: 12,
    fontFamily: 'Inter, sans-serif',
  },
  axisLine: { stroke: 'rgba(255,255,255,0.06)' },
  tickLine: false,
} as const;

// ── Shared grid props ─────────────────────────────────────────────────────────
export const gridProps = {
  stroke: chartTheme.gridColor,
  strokeDasharray: '3 3',
} as const;

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  formatter?: (value: number, name: string) => string;
}

export function CustomTooltip({ active, payload, label, formatter }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-card px-3 py-2 shadow-floating text-body-sm"
      style={{
        background: chartTheme.tooltipBg,
        border: `1px solid ${chartTheme.tooltipBorder}`,
        color: chartTheme.tooltipText,
      }}
    >
      {label && <p className="text-caption text-[var(--text-secondary)] mb-1.5">{label}</p>}
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
          <span className="text-[var(--text-secondary)]">{p.name}:</span>
          <span className="font-medium" style={{ color: chartTheme.tooltipText }}>
            {formatter ? formatter(p.value, p.name) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Chart container wrapper ────────────────────────────────────────────────────
interface ChartWrapperProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function ChartWrapper({ title, children, className, action }: ChartWrapperProps) {
  return (
    <div className={`glass rounded-card p-6 shadow-raised ${className ?? ''}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-h3 text-[var(--text-primary)]">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

// ── Shared color palette for charts ──────────────────────────────────────────
export const CHART_COLORS = chartTheme.colors;
