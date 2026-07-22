/**
 * pages/StyleGuide.tsx — Dev-only visual QA route.
 * Renders every variant of every design system component.
 * Route: /style-guide (only accessible in dev, not linked from nav)
 *
 * VERIFICATION CHECKLIST before building real pages:
 * [ ] Typography scale renders at correct sizes
 * [ ] All Button variants have correct hover/disabled states
 * [ ] Card variants render with glassmorphism
 * [ ] Form controls have focus glow
 * [ ] Skeletons shimmer correctly
 * [ ] Toast slides in with spring
 * [ ] Priority ring SVG renders correctly
 * [ ] Sub-score bars animate on hover
 */
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  BookOpen, Brain, Bell, Trash2, Plus, Check,
  BarChart2, TrendingUp, Calendar, Clock, Zap,
} from 'lucide-react';
import { fadeSlideIn } from '@/lib/motion';
import {
  Button, Card, Input, Select, DateInput, Checkbox, Toggle, Textarea,
  Label, Field, Skeleton, Badge, PriorityBadge, TaskTypeBadge, iconSize,
  ToastContainer,
} from '@/components/ui';
import type { ToastData } from '@/components/ui';

// ── Section wrapper ────────────────────────────────────────────────────────────
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-12">
      <h2 className="text-h2 text-[var(--text-primary)] mb-2">{title}</h2>
      <div className="h-px bg-[var(--card-border)] mb-6" />
      {children}
    </section>
  );
}

export default function StyleGuide() {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const [toggleOn, setToggleOn] = useState(false);
  const [checked, setChecked] = useState(false);
  const [inputError, setInputError] = useState('');

  const addToast = (tier: ToastData['urgency_tier']) => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, {
      id,
      urgency_tier: tier,
      title: tier === 'critical' ? '🚨 Physics Exam — Due Today!' : tier === 'high' ? '⚠️ CS Project Due Soon' : '📅 Chemistry Quiz Upcoming',
      message: tier === 'critical'
        ? 'Your Physics Mechanics exam is due today. Start studying now with focused Pomodoro sessions.'
        : 'Reminder: prioritize this task in your study plan today.',
      duration: 6000,
    }]);
  };

  const dismissToast = (id: string) => setToasts((p) => p.filter((t) => t.id !== id));

  const mockTask = {
    title: 'Physics Mechanics Final Exam',
    subject: 'Physics',
    taskType: 'exam',
    dueDate: new Date(Date.now() + 2 * 86400000).toISOString(),
    priorityScore: 88,
    urgencyScore: 8,
    importanceScore: 10,
    weaknessScore: 6,
    effortScore: 7,
    aiExplanation: 'Physics is top priority — exam due in 2 day(s) and your completion rate on this subject is lower than average.',
  };

  return (
    <motion.div
      variants={fadeSlideIn}
      initial="initial"
      animate="animate"
      className="min-h-screen p-12 max-w-5xl mx-auto"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="mb-12">
        <p className="text-caption text-[var(--info)] mb-2 uppercase tracking-widest">Dev Only · Not linked in nav</p>
        <h1 className="text-h1 text-[var(--text-primary)] mb-2">Design System Style Guide</h1>
        <p className="text-body text-[var(--text-secondary)]">
          Every variant of every component. Verify visually before building pages.
        </p>
      </div>

      {/* ── 1. Typography ───────────────────────────────────────────────────── */}
      <Section title="1. Typography Scale">
        <div className="space-y-4 glass rounded-card p-6">
          {[
            { cls: 'text-display', label: 'display — 36px/700', sample: '88' },
            { cls: 'text-h1',      label: 'h1 — 28px/600',     sample: 'Smart Study Reminder AI' },
            { cls: 'text-h2',      label: 'h2 — 20px/600',     sample: "Today's Study Plan" },
            { cls: 'text-h3',      label: 'h3 — 16px/600',     sample: 'Physics Mechanics Exam' },
            { cls: 'text-body',    label: 'body — 14px/400',    sample: 'Focus on Physics first: exam in 2 days with major academic weight.' },
            { cls: 'text-body-sm', label: 'body-sm — 13px/400', sample: 'Physics · Due in 2 days' },
            { cls: 'text-caption', label: 'caption — 12px/500', sample: 'HIGH PRIORITY · EXAM' },
          ].map(({ cls, label, sample }) => (
            <div key={cls} className="flex items-baseline gap-6">
              <span className="text-caption text-[var(--text-muted)] w-40 flex-shrink-0">{label}</span>
              <span className={`${cls} text-[var(--text-primary)]`}>{sample}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* ── 2. Color Palette ────────────────────────────────────────────────── */}
      <Section title="2. Color Palette">
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Priority High', color: 'var(--priority-high)' },
            { label: 'Priority Medium', color: 'var(--priority-medium)' },
            { label: 'Priority Low', color: 'var(--priority-low)' },
            { label: 'Info', color: 'var(--info)' },
            { label: 'Success', color: 'var(--success)' },
            { label: 'Warning', color: 'var(--warning)' },
            { label: 'Danger', color: 'var(--danger)' },
            { label: 'Text Primary', color: 'var(--text-primary)' },
            { label: 'Text Secondary', color: 'var(--text-secondary)' },
            { label: 'Card BG', color: 'var(--card-bg)', border: true },
            { label: 'BG Primary', color: 'var(--bg-primary)', border: true },
            { label: 'BG Secondary', color: 'var(--bg-secondary)', border: true },
          ].map(({ label, color, border }) => (
            <div key={label} className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-badge flex-shrink-0"
                style={{ backgroundColor: color, border: border ? '1px solid var(--card-border)' : undefined }}
              />
              <span className="text-caption text-[var(--text-secondary)]">{label}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* ── 3. Buttons ──────────────────────────────────────────────────────── */}
      <Section title="3. Button Variants">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <Button variant="primary">Primary Action</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="icon" icon={<Plus size={iconSize.button} />} />
            <Button variant="primary" loading>Loading</Button>
            <Button variant="primary" disabled>Disabled</Button>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <Button variant="primary" size="sm" icon={<Plus size={iconSize.inline} />}>Small</Button>
            <Button variant="primary" size="md">Medium</Button>
            <Button variant="primary" size="lg">Large</Button>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <Button variant="secondary" icon={<Bell size={iconSize.button} />}>With Icon</Button>
            <Button variant="destructive" icon={<Trash2 size={iconSize.button} />}>Delete</Button>
          </div>
        </div>
      </Section>

      {/* ── 4. Cards ────────────────────────────────────────────────────────── */}
      <Section title="4. Card Variants">
        <div className="grid grid-cols-2 gap-6 mb-6">
          <Card.Default>
            <h3 className="text-h3 text-[var(--text-primary)] mb-2">Card.Default</h3>
            <p className="text-body text-[var(--text-secondary)]">Standard glassmorphic container. Used for sections and info panels.</p>
          </Card.Default>

          <Card.Stat
            label="Completion Rate"
            value={73}
            unit="%"
            trend="up"
            trendValue="+12% this week"
            icon={<TrendingUp size={iconSize.button} />}
            accentColor="var(--success)"
          />
        </div>

        <div className="mb-6">
          <p className="text-caption text-[var(--text-secondary)] mb-3">Card.Task — hover to reveal sub-score breakdown</p>
          <Card.Task {...mockTask} />
        </div>

        <Card.Empty
          icon={<BookOpen size={iconSize.feature} />}
          title="No tasks scheduled today"
          description="Nothing scheduled today. Enjoy your free time or add a new assignment."
          action={{ label: 'Add Task', onClick: () => {} }}
        />
      </Section>

      {/* ── 5. Form Controls ────────────────────────────────────────────────── */}
      <Section title="5. Form Controls">
        <div className="glass rounded-card p-6 grid grid-cols-2 gap-6">
          <Field label="Text Input" htmlFor="input-demo">
            <Input id="input-demo" placeholder="Enter task title..." leftIcon={<BookOpen size={iconSize.inline} />} />
          </Field>

          <Field label="Input with Error" htmlFor="input-error" error="This field is required">
            <Input id="input-error" placeholder="Enter value..." error="required" />
          </Field>

          <Field label="Select" htmlFor="select-demo">
            <Select
              id="select-demo"
              placeholder="Choose type..."
              options={[
                { value: 'exam', label: 'Exam' },
                { value: 'assignment', label: 'Assignment' },
                { value: 'quiz', label: 'Quiz' },
              ]}
            />
          </Field>

          <Field label="Date & Time" htmlFor="date-demo">
            <DateInput id="date-demo" />
          </Field>

          <Field label="Textarea" htmlFor="textarea-demo">
            <Textarea id="textarea-demo" placeholder="Add description..." />
          </Field>

          <div className="space-y-4">
            <Checkbox
              id="check-demo"
              label="Mark as completed"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            <Toggle
              id="toggle-demo"
              label={toggleOn ? 'Reminders On' : 'Reminders Off'}
              checked={toggleOn}
              onChange={setToggleOn}
            />
          </div>
        </div>
      </Section>

      {/* ── 6. Badges ───────────────────────────────────────────────────────── */}
      <Section title="6. Badges & Tags">
        <div className="flex flex-wrap gap-3">
          <PriorityBadge score={88} />
          <PriorityBadge score={62} />
          <PriorityBadge score={40} />
          <PriorityBadge score={20} />
          {['exam', 'project', 'assignment', 'quiz', 'homework', 'reading'].map((t) => (
            <TaskTypeBadge key={t} type={t} />
          ))}
          <Badge color="var(--info)">Custom Badge</Badge>
        </div>
      </Section>

      {/* ── 7. Skeletons ────────────────────────────────────────────────────── */}
      <Section title="7. Skeleton Loading States">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <Skeleton.StatCard />
          <Skeleton.StatCard />
          <Skeleton.StatCard />
        </div>
        <Skeleton.TaskList count={2} className="mb-4" />
        <Skeleton.Chart />
      </Section>

      {/* ── 8. Toast Notifications ──────────────────────────────────────────── */}
      <Section title="8. Toast Notifications (spring animation)">
        <div className="flex gap-3">
          <Button variant="destructive" onClick={() => addToast('critical')} icon={<Bell size={iconSize.button} />}>
            Fire Critical Toast
          </Button>
          <Button variant="secondary" onClick={() => addToast('high')} icon={<Bell size={iconSize.button} />}>
            Fire High Toast
          </Button>
          <Button variant="secondary" onClick={() => addToast('medium')} icon={<Bell size={iconSize.button} />}>
            Fire Medium Toast
          </Button>
        </div>
        <p className="text-body-sm text-[var(--text-secondary)] mt-3">
          Toasts appear bottom-right with spring animation, auto-dismiss after 6s.
        </p>
      </Section>

      {/* ── 9. Motion Showcase ──────────────────────────────────────────────── */}
      <Section title="9. Elevation Levels">
        <div className="flex gap-6">
          {[
            { label: 'flat', shadow: 'none' },
            { label: 'raised', shadow: 'var(--shadow-raised)' },
            { label: 'floating', shadow: 'var(--shadow-floating)' },
          ].map(({ label, shadow }) => (
            <div
              key={label}
              className="glass rounded-card p-6 flex-1 text-center"
              style={{ boxShadow: shadow }}
            >
              <p className="text-h3 text-[var(--text-primary)]">{label}</p>
              <p className="text-caption text-[var(--text-secondary)] mt-1">{shadow === 'none' ? 'no shadow' : shadow}</p>
            </div>
          ))}
        </div>
      </Section>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </motion.div>
  );
}
