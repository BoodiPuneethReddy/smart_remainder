/**
 * pages/Tasks.tsx — Task management page.
 * Add/view/complete/delete tasks. Sorted by priority score.
 * Add task modal with full form. Filter by type/subject.
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Filter, X, ClipboardList, Upload } from 'lucide-react';
import { tasksApi, plannerApi, type Task } from '@/lib/api';
import {
  Button, Card, Field, Input, Select, DateInput, Textarea,
  Skeleton, iconSize,
} from '@/components/ui';
import { TaskTypeBadge } from '@/components/ui';
import { fadeSlideIn, staggerContainer, scaleIn } from '@/lib/motion';
import { format } from 'date-fns';
import ImportModal from '@/components/ui/ImportModal';

const TYPE_OPTIONS = [
  { value: 'exam', label: 'Exam' },
  { value: 'project', label: 'Project' },
  { value: 'assignment', label: 'Assignment' },
  { value: 'quiz', label: 'Quiz' },
  { value: 'homework', label: 'Homework' },
  { value: 'reading', label: 'Reading' },
];

const FILTER_OPTIONS = [
  { value: '', label: 'All Types' },
  ...TYPE_OPTIONS,
];

// ── Add Task Modal ────────────────────────────────────────────────────────────
function AddTaskModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: '', subject: '', description: '', task_type: 'assignment',
    due_date: '', estimated_hours: '2', grade_weight: '',
    exam_room: '', exam_duration_minutes: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { mutate: createTask, isPending } = useMutation({
    mutationFn: (data: any) => tasksApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['planner'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
      onClose();
    },
  });

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.title.trim()) e.title = 'Title is required';
    if (!form.subject.trim()) e.subject = 'Subject is required';
    if (!form.due_date) e.due_date = 'Due date is required';
    if (!form.estimated_hours || isNaN(+form.estimated_hours)) e.estimated_hours = 'Enter a valid number';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    createTask({
      ...form,
      estimated_hours: +form.estimated_hours,
      grade_weight: form.grade_weight ? +form.grade_weight : undefined,
      exam_duration_minutes: form.exam_duration_minutes ? +form.exam_duration_minutes : undefined,
    });
  };

  const set = (k: string) => (e: React.ChangeEvent<any>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
         onClick={(e) => e.target === e.currentTarget && onClose()}>
      <motion.div
        variants={scaleIn}
        initial="initial" animate="animate" exit="exit"
        className="w-full max-w-lg glass rounded-card shadow-floating overflow-y-auto max-h-[90vh]"
      >
        <div className="p-6 border-b border-[var(--card-border)] flex items-center justify-between">
          <h2 className="text-h2 text-[var(--text-primary)]">Add New Task</h2>
          <Button variant="icon" onClick={onClose} icon={<X size={iconSize.button} />} />
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Title" htmlFor="task-title" required error={errors.title} className="col-span-2">
              <Input id="task-title" placeholder="Physics Mechanics Exam" value={form.title} onChange={set('title')} error={errors.title} />
            </Field>
            <Field label="Subject" htmlFor="task-subject" required error={errors.subject}>
              <Input id="task-subject" placeholder="Physics" value={form.subject} onChange={set('subject')} error={errors.subject} />
            </Field>
            <Field label="Type" htmlFor="task-type">
              <Select id="task-type" options={TYPE_OPTIONS} value={form.task_type} onChange={set('task_type')} />
            </Field>
            <Field label="Due Date & Time" htmlFor="task-due" required error={errors.due_date}>
              <DateInput id="task-due" value={form.due_date} onChange={set('due_date')} error={errors.due_date} />
            </Field>
            <Field label="Estimated Hours" htmlFor="task-hours" required error={errors.estimated_hours}>
              <Input id="task-hours" type="number" min="0.5" step="0.5" placeholder="2" value={form.estimated_hours} onChange={set('estimated_hours')} error={errors.estimated_hours} />
            </Field>
            {(form.task_type === 'assignment' || form.task_type === 'project' || form.task_type === 'homework') && (
              <Field label="Grade Weight (%)" htmlFor="task-weight">
                <Input id="task-weight" type="number" min="0" max="100" placeholder="10" value={form.grade_weight} onChange={set('grade_weight')} />
              </Field>
            )}
            {form.task_type === 'exam' && (
              <>
                <Field label="Exam Room" htmlFor="task-room">
                  <Input id="task-room" placeholder="Hall B" value={form.exam_room} onChange={set('exam_room')} />
                </Field>
                <Field label="Duration (minutes)" htmlFor="task-duration">
                  <Input id="task-duration" type="number" placeholder="120" value={form.exam_duration_minutes} onChange={set('exam_duration_minutes')} />
                </Field>
              </>
            )}
            <Field label="Description" htmlFor="task-desc" className="col-span-2">
              <Textarea id="task-desc" placeholder="Add notes, requirements, or details..." value={form.description} onChange={set('description')} />
            </Field>
          </div>

          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={onClose} type="button">Cancel</Button>
            <Button variant="primary" className="flex-1" loading={isPending} type="submit">
              Create Task
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}

// ── Tasks Page ────────────────────────────────────────────────────────────────
export default function Tasks() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [filterType, setFilterType] = useState('');
  const [showCompleted, setShowCompleted] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', { filterType, showCompleted }],
    queryFn: () => tasksApi.list({
      include_completed: showCompleted,
      task_type: filterType || undefined,
    }).then((r) => r.data),
    staleTime: 30_000,
  });

  const { mutate: completeTask } = useMutation({
    mutationFn: (id: number) => tasksApi.update(id, { is_completed: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['planner'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });

  const { mutate: deleteTask } = useMutation({
    mutationFn: (id: number) => tasksApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const tasks = data?.tasks ?? [];

  return (
    <motion.div variants={fadeSlideIn} initial="initial" animate="animate" className="page-padding space-y-6 max-w-4xl">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-h1 text-[var(--text-primary)]">Tasks</h1>
          <p className="text-body-sm text-[var(--text-secondary)] mt-1">
            {data?.total ?? 0} tasks · sorted by AI priority score
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" id="import-document-btn" onClick={() => setShowImport(true)} className="flex items-center gap-2">
            <Upload size={iconSize.inline} />
            Import Document
          </Button>
          <Button variant="primary" icon={<Plus size={iconSize.button} />} onClick={() => setShowAdd(true)}>
            Add Task
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Filter size={iconSize.inline} className="text-[var(--text-muted)]" />
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilterType(opt.value)}
            className={`text-caption px-3 py-1.5 rounded-full border transition-all duration-150 ${
              filterType === opt.value
                ? 'border-[var(--info)] text-[var(--info)] bg-[rgba(91,141,239,0.1)]'
                : 'border-[var(--card-border)] text-[var(--text-secondary)] hover:border-[var(--text-muted)]'
            }`}
          >
            {opt.label}
          </button>
        ))}
        <button
          onClick={() => setShowCompleted(!showCompleted)}
          className={`text-caption px-3 py-1.5 rounded-full border ml-auto transition-all duration-150 ${
            showCompleted ? 'border-[var(--success)] text-[var(--success)] bg-[rgba(46,196,182,0.1)]' : 'border-[var(--card-border)] text-[var(--text-secondary)]'
          }`}
        >
          {showCompleted ? 'Hide Completed' : 'Show Completed'}
        </button>
      </div>

      {/* Task list */}
      {isLoading ? (
        <Skeleton.TaskList count={4} />
      ) : tasks.length === 0 ? (
        <Card.Empty
          icon={<ClipboardList size={iconSize.feature} />}
          title="No tasks found"
          description={filterType ? `No ${filterType} tasks. Try a different filter or add a new task.` : "You're all caught up! Add a new task to get started."}
          action={{ label: 'Add Task', onClick: () => setShowAdd(true) }}
        />
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-4">
          {tasks.map((task) => (
            <Card.Task
              key={task.id}
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
              isCompleted={task.is_completed}
              onComplete={() => completeTask(task.id)}
              onDelete={() => deleteTask(task.id)}
            />
          ))}
        </motion.div>
      )}

      {/* Add Task Modal */}
      <AnimatePresence>
        {showAdd && <AddTaskModal onClose={() => setShowAdd(false)} />}
      </AnimatePresence>

      {/* Import Modal */}
      <ImportModal
        isOpen={showImport}
        onClose={() => setShowImport(false)}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ['tasks'] });
          qc.invalidateQueries({ queryKey: ['planner'] });
          qc.invalidateQueries({ queryKey: ['analytics'] });
        }}
      />
    </motion.div>
  );
}
