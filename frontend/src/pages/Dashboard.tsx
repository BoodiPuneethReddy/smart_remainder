/**
 * pages/Dashboard.tsx — Main dashboard.
 *
 * Layout:
 *   Hero row: Today's Plan card (full width) + Top 3 Priority Task cards
 *   Secondary row: Completion % stat, Study Hours stat, Streak stat, Mini calendar
 *   Tertiary row: Weekly activity bar chart
 *
 * All data from live API. Skeleton screens during load.
 * Cards animate in with stagger on first paint.
 */
import React, { useEffect, useState, lazy, Suspense } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip,
} from 'recharts';
import {
  TrendingUp, Clock, Flame, BookOpen, CheckCircle2, AlertTriangle, Upload,
} from 'lucide-react';
import { plannerApi, analyticsApi, tasksApi, remindersApi, assessmentApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import {
  Card, Skeleton, iconSize, ToastContainer, Button,
} from '@/components/ui';
import { axisProps, gridProps, CustomTooltip, ChartWrapper } from '@/components/ui/ChartTheme';
import { chartTheme } from '@/lib/design-tokens';
import { fadeSlideIn, staggerContainer, staggerChild } from '@/lib/motion';
import { formatDuration, formatDate } from '@/lib/utils';
import { format } from 'date-fns';
import { Brain, Award } from 'lucide-react';
import ImportModal from '@/components/ui/ImportModal';

const AITutorWorkspace = lazy(() => import('@/components/ui/AITutorWorkspace'));

export default function Dashboard() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { toasts, addToast, dismissToast } = useToast();
  const [showImport, setShowImport] = useState(false);
  const [showAssessment, setShowAssessment] = useState(false);
  const [assessmentDocId, setAssessmentDocId] = useState<number | undefined>(undefined);

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ['planner', 'daily'],
    queryFn: () => plannerApi.daily().then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: weekly } = useQuery({
    queryKey: ['analytics', 'weekly'],
    queryFn: () => analyticsApi.weekly().then((r) => r.data),
    staleTime: 60_000,
  });

  // Poll for new reminders every 60s and show toasts
  const { mutate: checkReminders } = useMutation({
    mutationFn: () => remindersApi.check().then((r) => r.data),
    onSuccess: (notifications) => {
      notifications.forEach((n) => {
        addToast({
          title: n.title,
          message: n.message,
          urgency_tier: n.urgency_tier as any,
        });
      });
      if (notifications.length) qc.invalidateQueries({ queryKey: ['reminders'] });
    },
  });

  const { mutate: completeTask } = useMutation({
    mutationFn: (id: number) => tasksApi.update(id, { is_completed: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['planner'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
      qc.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  // Trigger reminder check on mount + every 60s
  useEffect(() => {
    checkReminders();
    const interval = setInterval(checkReminders, 60_000);
    return () => clearInterval(interval);
  }, [checkReminders]);

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <>
      <motion.div
        variants={fadeSlideIn}
        initial="initial"
        animate="animate"
        className="page-padding pt-8 space-y-8 max-w-7xl"
      >
        {/* Page header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-h1 text-[var(--text-primary)]">
              {greeting()}, {user?.full_name?.split(' ')[0] ?? 'Student'} 👋
            </h1>
            <p className="text-body-sm text-[var(--text-secondary)] mt-1">
              {format(new Date(), 'EEEE, MMMM d, yyyy')} · Here's what needs your attention today
            </p>
          </div>
          <Button
            variant="secondary"
            id="import-document-btn"
            onClick={() => setShowImport(true)}
            className="flex items-center gap-2"
          >
            <Upload size={iconSize.inline} />
            Import Document
          </Button>
        </div>

        {/* ── Hero row: Today's Plan ──────────────────────────────────────── */}
        {planLoading ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Skeleton.Card className="lg:col-span-1" />
            <Skeleton.TaskList count={3} className="lg:col-span-2" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* Today's plan summary card */}
            <Card.Default className="lg:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <Clock size={iconSize.button} style={{ color: 'var(--info)' }} />
                <h2 className="text-h2 text-[var(--text-primary)]">Today's Plan</h2>
              </div>
              <div className="space-y-3">
                <div>
                  <p className="text-caption text-[var(--text-secondary)] mb-1">Study time allocated</p>
                  <p className="text-display font-bold" style={{ color: 'var(--info)' }}>
                    {formatDuration(plan?.total_recommended_minutes ?? 0)}
                  </p>
                </div>
                <div className="h-px bg-[var(--card-border)]" />
                <div>
                  <p className="text-caption text-[var(--text-secondary)] mb-2">Tasks to cover</p>
                  {(plan?.tasks ?? []).slice(0, 5).map((t) => (
                    <div key={t.task_id} className="flex items-center justify-between py-1.5 border-b border-[var(--card-border)] last:border-0">
                      <span className="text-body-sm text-[var(--text-primary)] truncate mr-2">{t.subject}</span>
                      <span className="text-caption text-[var(--text-secondary)] flex-shrink-0">{t.recommended_minutes}m</span>
                    </div>
                  ))}
                  {(plan?.tasks?.length ?? 0) === 0 && (
                    <p className="text-body-sm text-[var(--text-secondary)]">All caught up! 🎉</p>
                  )}
                </div>
              </div>
            </Card.Default>

            {/* Top 3 Priority tasks */}
            <motion.div
              variants={staggerContainer}
              initial="initial"
              animate="animate"
              className="lg:col-span-2 space-y-4"
            >
              {(plan?.tasks ?? []).length === 0 ? (
                <Card.Empty
                  icon={<CheckCircle2 size={iconSize.feature} />}
                  title="Nothing scheduled today"
                  description="Enjoy your free time or add a new assignment to stay on track."
                  action={{ label: 'Add Task', onClick: () => window.location.href = '/tasks' }}
                />
              ) : (
                (plan?.tasks ?? []).slice(0, 3).map((task) => (
                  <Card.Task
                    key={task.task_id}
                    title={task.title}
                    subject={task.subject}
                    taskType={task.task_type}
                    dueDate={task.due_date}
                    priorityScore={task.priority_score}
                    urgencyScore={task.urgency_score}
                    importanceScore={task.importance_score}
                    weaknessScore={task.weakness_score}
                    effortScore={task.effort_score}
                    aiExplanation={task.ai_explanation}
                    onComplete={() => completeTask(task.task_id)}
                  />
                ))
              )}
            </motion.div>
          </div>
        )}

        {/* ── Secondary row: Stat cards ────────────────────────────────────── */}
        {analyticsLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <Skeleton.StatCard key={i} />)}
          </div>
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="grid grid-cols-2 lg:grid-cols-4 gap-4"
          >
            <motion.div variants={staggerChild}>
              <Card.Stat
                label="Completion Rate"
                value={analytics?.completion_rate ?? 0}
                unit="%"
                trend="up"
                trendValue={`${analytics?.completed_tasks}/${analytics?.total_tasks} tasks`}
                icon={<TrendingUp size={iconSize.button} />}
                accentColor="var(--success)"
              />
            </motion.div>
            <motion.div variants={staggerChild}>
              <Card.Stat
                label="Study Hours"
                value={(((analytics?.total_study_minutes ?? 0) / 60)).toFixed(1)}
                unit="hrs"
                icon={<Clock size={iconSize.button} />}
                accentColor="var(--info)"
              />
            </motion.div>
            <motion.div variants={staggerChild}>
              <Card.Stat
                label="Study Streak"
                value={analytics?.streak_days ?? 0}
                unit="days"
                trend={analytics?.streak_days ? 'up' : 'flat'}
                trendValue="Keep it going!"
                icon={<Flame size={iconSize.button} />}
                accentColor="var(--priority-medium)"
              />
            </motion.div>
            <motion.div variants={staggerChild}>
              <Card.Stat
                label="Avg Priority"
                value={Math.round(analytics?.avg_priority_score ?? 0)}
                unit="/100"
                icon={<AlertTriangle size={iconSize.button} />}
                accentColor="var(--priority-high)"
              />
            </motion.div>
          </motion.div>
        )}

        {/* ── Learning Intelligence & Weekly Activity row ────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          
          {/* AI Learning Workspace Card */}
          <div className="lg:col-span-2">
            <Card.Default>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Brain size={iconSize.button} className="text-blue-500" />
                  <h2 className="text-h2 text-[var(--text-primary)]">AI Study Workspace</h2>
                </div>
                <span className="text-caption text-[var(--text-secondary)]">Document-First Learning Engine</span>
              </div>

              <div className="p-6 rounded-xl border border-white/5 bg-white/5 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mx-auto">
                  <BookOpen size={32} />
                </div>
                <div>
                  <h3 className="text-h3 text-white font-bold">Document-Guided AI Tutoring</h3>
                  <p className="text-body-sm text-[var(--text-secondary)] mt-1 max-w-md mx-auto">
                    Upload lecture notes, textbooks, or class PDFs to start a sequential AI study session tailored to your document.
                  </p>
                </div>
                <div className="flex justify-center gap-3 pt-2">
                  <Button
                    variant="primary"
                    onClick={() => {
                      setAssessmentDocId(undefined);
                      setShowAssessment(true);
                    }}
                    className="flex items-center gap-2"
                  >
                    <Brain size={16} />
                    <span>Open Learning Workspace</span>
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setShowImport(true)}
                    className="flex items-center gap-2"
                  >
                    <Upload size={16} />
                    <span>Upload Study PDF</span>
                  </Button>
                </div>
              </div>
            </Card.Default>
          </div>

          {/* Weekly activity chart */}
          <div className="lg:col-span-1 h-full">
            {!weekly ? (
              <Skeleton.Chart />
            ) : (
              <ChartWrapper title="Weekly Activity">
                <ResponsiveContainer width="100%" height={252}>
                  <BarChart data={weekly.weekly_data} barGap={4}>
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => format(new Date(v), 'EEE')}
                      {...axisProps}
                    />
                    <YAxis {...axisProps} allowDecimals={false} width={28} />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                    <Bar dataKey="completed" name="Completed" fill={chartTheme.colors[2]} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="added" name="Added" fill={chartTheme.colors[3]} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartWrapper>
            )}
          </div>

        </div>
      </motion.div>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <ImportModal
        isOpen={showImport}
        onClose={() => setShowImport(false)}
        onSuccess={(result) => {
          addToast({
            title: "Import Successful",
            message: `Created ${result.tasksCreated} new tasks from your document.`,
            urgency_tier: "medium",
          });
          qc.invalidateQueries({ queryKey: ['planner'] });
          qc.invalidateQueries({ queryKey: ['analytics'] });
          qc.invalidateQueries({ queryKey: ['tasks'] });
          qc.invalidateQueries({ queryKey: ['assessment'] });
        }}
      />

      <Suspense fallback={null}>
        {showAssessment && (
          <AITutorWorkspace
            isOpen={showAssessment}
            onClose={() => setShowAssessment(false)}
            documentId={assessmentDocId}
            onSuccess={() => {
              addToast({
                title: "Study Block Evaluated",
                message: "Your mastery, retention, and learning objectives have been updated in the Socratic registry.",
                urgency_tier: "medium",
              });
              qc.invalidateQueries({ queryKey: ['planner'] });
              qc.invalidateQueries({ queryKey: ['analytics'] });
              qc.invalidateQueries({ queryKey: ['tasks'] });
              qc.invalidateQueries({ queryKey: ['assessment'] });
            }}
          />
        )}
      </Suspense>
    </>
  );
}
