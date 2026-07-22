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
  const [assessmentSubject, setAssessmentSubject] = useState('');
  const [assessmentTopic, setAssessmentTopic] = useState('');
  const [assessmentDocId, setAssessmentDocId] = useState<number | undefined>(undefined);

  const { data: learningProfile, isLoading: profileLoading } = useQuery({
    queryKey: ['assessment', 'learning-profile'],
    queryFn: () => assessmentApi.getLearningProfile().then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: mistakeJournal } = useQuery({
    queryKey: ['assessment', 'mistake-journal'],
    queryFn: () => assessmentApi.listMistakes().then((r) => r.data),
    staleTime: 30_000,
  });

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

  const renderAsciiBar = (percentage: number) => {
    const totalBlocks = 10;
    const filledBlocks = Math.round((percentage / 100) * totalBlocks);
    const emptyBlocks = totalBlocks - filledBlocks;
    return '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);
  };

  const getRevisionLabel = (lastRevisionStr: string, intervalDays: number) => {
    const lastRev = new Date(lastRevisionStr);
    const now = new Date();
    const dueTime = lastRev.getTime() + (intervalDays * 24 * 60 * 60 * 1000);
    const diffMs = dueTime - now.getTime();
    const diffDays = Math.ceil(diffMs / (24 * 60 * 60 * 1000));
    
    if (diffDays <= 0) {
      return { text: "Due Today", style: "text-red-400 bg-red-500/10 border border-red-500/20" };
    }
    if (diffDays === 1) {
      return { text: "Tomorrow", style: "text-orange-400 bg-orange-500/10 border border-orange-500/20" };
    }
    return { text: `In ${diffDays} days`, style: "text-blue-400 bg-blue-500/10 border border-blue-500/20" };
  };

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
          
          {/* Learning Intelligence Card */}
          <div className="lg:col-span-2">
            <Card.Default>
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Brain size={iconSize.button} className="text-orange-500" />
                  <h2 className="text-h2 text-[var(--text-primary)]">Learning Agent</h2>
                </div>
                <span className="text-caption text-[var(--text-secondary)]">Adaptive Mastery & Retention Curve</span>
              </div>

              {profileLoading ? (
                <Skeleton.TaskList count={3} />
              ) : !learningProfile || learningProfile.length === 0 ? (
                <div className="text-center py-8 text-[var(--text-secondary)] space-y-4">
                  <p className="text-caption">No active learning topics found. Upload academic documents or Timetables to start testing.</p>
                  <Button
                    variant="secondary"
                    className="mx-auto"
                    onClick={() => {
                      setAssessmentSubject("Mathematics");
                      setAssessmentTopic("Core Calculus");
                      setAssessmentDocId(undefined);
                      setShowAssessment(true);
                    }}
                  >
                    Diagnose Initial Knowledge
                  </Button>
                </div>
              ) : (
                <div className="space-y-4 max-h-[320px] overflow-y-auto pr-2">
                  {learningProfile.map((p) => {
                    const revision = getRevisionLabel(p.last_revision, p.interval_days);
                    return (
                      <div
                        key={p.id}
                        className="p-4 rounded-xl border border-white/5 bg-white/5 space-y-4 hover:bg-white/10 transition-all"
                      >
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          <div className="space-y-0.5">
                            <span className="text-[10px] font-bold text-orange-500 uppercase tracking-wider block">
                              {p.subject}
                            </span>
                            <span className="text-body-sm font-semibold text-white block">
                              {p.topic}
                            </span>
                          </div>

                          <div className="flex flex-wrap items-center gap-6 text-[12px] font-mono">
                            {/* Mastery visual bar */}
                            <div className="space-y-0.5">
                              <span className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] block">
                                Mastery
                              </span>
                              <div className="flex items-center gap-2">
                                <span className="text-orange-400 font-bold text-[11px]">
                                  {renderAsciiBar(p.mastery)}
                                </span>
                                <span className="text-white font-bold">{Math.round(p.mastery)}%</span>
                              </div>
                            </div>

                            {/* Retention curve visual bar */}
                            <div className="space-y-0.5">
                              <span className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] block">
                                Retention
                              </span>
                              <div className="flex items-center gap-2">
                                <span className="text-emerald-400 font-bold text-[11px]">
                                  {renderAsciiBar(p.retention)}
                                </span>
                                <span className="text-white font-bold">{Math.round(p.retention)}%</span>
                              </div>
                            </div>

                            {/* Revision Due Schedule */}
                            <div className="space-y-0.5">
                              <span className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] block">
                                Revision
                              </span>
                              <span className={`px-2 py-0.5 rounded text-[11px] font-sans font-medium block text-center ${revision.style}`}>
                                {revision.text}
                              </span>
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <button
                              onClick={() => {
                                setAssessmentSubject(p.subject);
                                setAssessmentTopic(p.topic);
                                setShowAssessment(true);
                              }}
                              className="px-3.5 py-1.5 rounded-lg border border-orange-500/30 text-orange-400 hover:bg-orange-500/10 text-caption font-semibold transition-all hover:scale-[1.02]"
                            >
                              Study Workspace
                            </button>
                          </div>
                        </div>

                        {/* Collapsible Knowledge Map Visual Tree */}
                        <div className="pl-4 border-l-2 border-white/10 space-y-2 text-[11px] font-mono text-[var(--text-secondary)]">
                          <div className="flex items-center justify-between text-[10px] uppercase text-white/30 font-sans tracking-wider pb-1">
                            <span>Knowledge Map Tree Nodes (Click to Focus Tutor)</span>
                            <span>Status</span>
                          </div>
                          {p.topic.toLowerCase().includes('calculus') ? (
                            <>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Limits & Continuity");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>├── Limits & Continuity</span>
                                <span className="text-[9px] font-sans font-bold">Mastered ✓</span>
                              </div>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Derivatives Fundamentals");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>├── Derivatives Fundamentals</span>
                                <span className="text-[9px] font-sans font-bold">Mastered ✓</span>
                              </div>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Integrals & Area Anomalies");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-orange-400 bg-orange-500/5 hover:bg-orange-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>├── Integrals & Area Anomalies</span>
                                <span className="text-[9px] font-sans font-bold">Weak ⚠</span>
                              </div>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Differential Equations");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-red-400 bg-red-500/5 hover:bg-red-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>└── Differential Equations</span>
                                <span className="text-[9px] font-sans font-bold">Very Weak ❌</span>
                              </div>
                            </>
                          ) : (
                            <>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Fundamentals & Terms");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>├── Fundamentals & Terms</span>
                                <span className="text-[9px] font-sans font-bold">Mastered ✓</span>
                              </div>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Core Structures & Relations");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-orange-400 bg-orange-500/5 hover:bg-orange-500/15 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>├── Core Structures & Relations</span>
                                <span className="text-[9px] font-sans font-bold">Weak ⚠</span>
                              </div>
                              <div
                                onClick={() => {
                                  setAssessmentSubject(p.subject);
                                  setAssessmentTopic("Advanced Production Scenarios");
                                  setShowAssessment(true);
                                }}
                                className="flex items-center justify-between text-white/40 bg-white/2 hover:bg-white/5 px-2 py-1 rounded cursor-pointer transition-colors"
                              >
                                <span>└── Advanced Production Scenarios</span>
                                <span className="text-[9px] font-sans">Locked</span>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Source Syllabus Coverage Tracker */}
              <div className="mt-6 p-4 rounded-xl border border-white/5 bg-white/2 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-caption font-bold text-white uppercase tracking-wider block">Uploaded Sources Coverage</span>
                  <span className="text-h3 text-orange-500 font-mono">82% Coverage</span>
                </div>
                <div className="space-y-2 text-[11px] font-mono">
                  <div className="flex justify-between text-emerald-400 bg-emerald-500/5 p-2 rounded">
                    <span>✓ Academic Timetable / Syllabus</span>
                    <span>Uploaded</span>
                  </div>
                  <div className="flex justify-between text-emerald-400 bg-emerald-500/5 p-2 rounded">
                    <span>✓ Reference Book Chapters (Calculus/DBMS)</span>
                    <span>Uploaded</span>
                  </div>
                  <div className="flex justify-between text-red-400 bg-red-500/5 p-2 rounded">
                    <span>✗ Homework Assignment 3 Exercises</span>
                    <span>Missing</span>
                  </div>
                </div>
              </div>

              {/* Mistake Journal Pane */}
              {mistakeJournal && mistakeJournal.length > 0 && (
                <div className="mt-6 p-4 rounded-xl border border-red-500/20 bg-red-500/5 space-y-3">
                  <span className="text-caption font-bold text-red-400 uppercase tracking-wider block">Mistake Journal</span>
                  <div className="space-y-3">
                    {mistakeJournal.slice(0, 3).map((m: any) => (
                      <div key={m.id} className="p-3 rounded-lg border border-red-500/10 bg-red-500/10 space-y-1 font-sans">
                        <div className="flex justify-between text-caption font-bold text-red-400">
                          <span>{m.subject} - {m.topic}</span>
                          <span>{m.mistakes_count} Gaps</span>
                        </div>
                        <p className="text-[11px] text-white/70 italic leading-relaxed">
                          "{m.question_text}"
                        </p>
                        <div className="text-[9px] text-white/40">
                          Revision due: Tomorrow
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
            subject={assessmentSubject}
            topic={assessmentTopic}
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
