/**
 * pages/Analytics.tsx — Analytics and performance insights.
 * Charts: weekly activity bar, subject performance radar, task type breakdown donut.
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  PieChart, Pie, Cell, Tooltip, Legend,
} from 'recharts';
import { BarChart2, BookOpen, Target, Flame } from 'lucide-react';
import { analyticsApi } from '@/lib/api';
import { Card, Skeleton, iconSize } from '@/components/ui';
import { axisProps, gridProps, CustomTooltip, ChartWrapper, CHART_COLORS } from '@/components/ui/ChartTheme';
import { chartTheme, colors } from '@/lib/design-tokens';
import { fadeSlideIn, staggerContainer, staggerChild } from '@/lib/motion';
import { formatDuration } from '@/lib/utils';
import { format } from 'date-fns';

export default function Analytics() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
    staleTime: 60_000,
  });
  const { data: weekly } = useQuery({
    queryKey: ['analytics', 'weekly'],
    queryFn: () => analyticsApi.weekly().then((r) => r.data),
    staleTime: 60_000,
  });

  if (isLoading) return (
    <div className="page-padding space-y-6 max-w-7xl">
      <Skeleton height={40} width={200} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton.StatCard key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton.Chart /><Skeleton.Chart />
      </div>
    </div>
  );

  const subjects = analytics?.subjects ?? [];
  const pendingByType = Object.entries(analytics?.pending_by_type ?? {}).map(([name, value]) => ({ name, value }));

  const radarData = subjects.slice(0, 6).map((s) => ({
    subject: s.subject,
    completion: s.completion_rate,
    priority: s.avg_priority_score,
  }));

  return (
    <motion.div variants={fadeSlideIn} initial="initial" animate="animate"
                className="page-padding space-y-6 max-w-7xl">
      <div>
        <h1 className="text-h1 text-[var(--text-primary)]">Analytics</h1>
        <p className="text-body-sm text-[var(--text-secondary)] mt-1">Performance insights and study patterns</p>
      </div>

      {/* Stat summary row */}
      <motion.div variants={staggerContainer} initial="initial" animate="animate"
                  className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Completion Rate', value: `${analytics?.completion_rate ?? 0}%`, icon: <Target size={iconSize.button} />, color: colors.success },
          { label: 'Study Hours', value: formatDuration(analytics?.total_study_minutes ?? 0), icon: <BookOpen size={iconSize.button} />, color: colors.info },
          { label: 'Study Streak', value: `${analytics?.streak_days ?? 0} days`, icon: <Flame size={iconSize.button} />, color: colors.priorityMedium },
          { label: 'Active Tasks', value: `${(analytics?.total_tasks ?? 0) - (analytics?.completed_tasks ?? 0)}`, icon: <BarChart2 size={iconSize.button} />, color: colors.priorityHigh },
        ].map((s) => (
          <motion.div key={s.label} variants={staggerChild}>
            <Card.Stat label={s.label} value={s.value} icon={s.icon} accentColor={s.color} />
          </motion.div>
        ))}
      </motion.div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly activity */}
        <ChartWrapper title="Weekly Activity">
          {(weekly?.weekly_data ?? []).length === 0 ? (
            <div className="h-40 flex items-center justify-center">
              <p className="text-body-sm text-[var(--text-secondary)]">No session data yet. Start studying to see your activity.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weekly?.weekly_data ?? []} barGap={4}>
                <XAxis dataKey="date" tickFormatter={(v) => format(new Date(v), 'EEE')} {...axisProps} />
                <YAxis {...axisProps} allowDecimals={false} width={28} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="completed" name="Completed" fill={CHART_COLORS[2]} radius={[4, 4, 0, 0]} />
                <Bar dataKey="study_minutes" name="Study min" fill={CHART_COLORS[3]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartWrapper>

        {/* Task type breakdown */}
        <ChartWrapper title="Pending Tasks by Type">
          {pendingByType.length === 0 ? (
            <div className="h-40 flex items-center justify-center">
              <p className="text-body-sm text-[var(--text-secondary)]">All tasks completed! 🎉</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pendingByType} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                     labelLine={false}>
                  {pendingByType.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartWrapper>

        {/* Subject completion radar */}
        <ChartWrapper title="Subject Performance Radar" className="lg:col-span-2">
          {radarData.length === 0 ? (
            <div className="h-48 flex items-center justify-center">
              <p className="text-body-sm text-[var(--text-secondary)]">Complete some tasks to see subject performance.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={radarData}>
                <PolarGrid stroke={chartTheme.gridColor} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: chartTheme.axisColor, fontSize: 12 }} />
                <Radar name="Completion %" dataKey="completion" stroke={CHART_COLORS[2]} fill={CHART_COLORS[2]} fillOpacity={0.25} />
                <Radar name="Avg Priority" dataKey="priority" stroke={CHART_COLORS[0]} fill={CHART_COLORS[0]} fillOpacity={0.15} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: chartTheme.axisColor, fontSize: 12 }} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </ChartWrapper>
      </div>

      {/* Subject table */}
      <Card.Default>
        <h2 className="text-h2 text-[var(--text-primary)] mb-4">Subject Breakdown</h2>
        {subjects.length === 0 ? (
          <p className="text-body-sm text-[var(--text-secondary)]">No subject data yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-body-sm">
              <thead>
                <tr className="border-b border-[var(--card-border)]">
                  {['Subject', 'Tasks', 'Completion', 'Study Time', 'Avg Priority'].map((h) => (
                    <th key={h} className="text-left py-2 pr-4 text-caption text-[var(--text-secondary)] font-medium uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {subjects.map((s) => (
                  <tr key={s.subject} className="border-b border-[var(--card-border)] last:border-0 hover:bg-[var(--surface-hover)] transition-colors">
                    <td className="py-3 pr-4 text-[var(--text-primary)] font-medium">{s.subject}</td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{s.completed_tasks}/{s.total_tasks}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1.5 rounded-full bg-white/8 overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${s.completion_rate}%`, background: 'var(--success)' }} />
                        </div>
                        <span className="text-[var(--text-secondary)]">{s.completion_rate}%</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-[var(--text-secondary)]">{formatDuration(s.total_study_minutes)}</td>
                    <td className="py-3">
                      <span className="font-semibold" style={{ color: s.avg_priority_score >= 70 ? 'var(--priority-high)' : s.avg_priority_score >= 45 ? 'var(--priority-medium)' : 'var(--priority-low)' }}>
                        {s.avg_priority_score.toFixed(0)}/100
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card.Default>
    </motion.div>
  );
}
