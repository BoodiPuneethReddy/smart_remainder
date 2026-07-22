import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { formatDistanceToNow, format, differenceInDays } from 'date-fns';

/** Merge Tailwind classes safely — use this everywhere instead of string concatenation. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format a date for display. */
export function formatDate(date: string | Date): string {
  return format(new Date(date), 'MMM d, yyyy');
}

/** "3 days ago", "in 2 hours" etc. */
export function formatRelative(date: string | Date): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

/** Days remaining until due date (negative = overdue). */
export function daysUntil(dueDate: string | Date): number {
  return differenceInDays(new Date(dueDate), new Date());
}

/** Human-readable days-remaining label. */
export function daysLabel(days: number): string {
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return 'Due today';
  if (days === 1) return 'Due tomorrow';
  return `Due in ${days}d`;
}

/** Format study duration in minutes → human string. */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/** Clamp a number between min and max. */
export function clamp(val: number, min: number, max: number): number {
  return Math.min(Math.max(val, min), max);
}
