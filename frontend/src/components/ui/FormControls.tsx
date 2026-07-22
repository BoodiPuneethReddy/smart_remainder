/**
 * components/ui/FormControls.tsx — All form elements, styled once.
 *
 * Controls: Input, Select, DateInput, Checkbox, Toggle
 * Every control: 40px height, 14px radius, focus-glow, error state with inline message.
 */
import React, { forwardRef } from 'react';
import { cn } from '@/lib/utils';

const baseInput = [
  'w-full h-10 px-3 rounded-input',
  'bg-[var(--bg-secondary)] border border-[var(--card-border)]',
  'text-body text-[var(--text-primary)] placeholder:text-[var(--text-muted)]',
  'transition-all duration-150 outline-none',
  'focus:border-[var(--info)] focus:shadow-[0_0_0_3px_var(--focus-ring)]',
  'disabled:opacity-40 disabled:cursor-not-allowed',
].join(' ');

const errorInput = 'border-[var(--danger)] focus:border-[var(--danger)] focus:shadow-[0_0_0_3px_rgba(255,107,53,0.25)]';

// ── Label ─────────────────────────────────────────────────────────────────────
interface LabelProps { htmlFor?: string; children: React.ReactNode; required?: boolean; }
export function Label({ htmlFor, children, required }: LabelProps) {
  return (
    <label htmlFor={htmlFor} className="block text-caption text-[var(--text-secondary)] mb-1.5 font-medium">
      {children}{required && <span className="text-[var(--danger)] ml-0.5">*</span>}
    </label>
  );
}

// ── Field wrapper ─────────────────────────────────────────────────────────────
interface FieldProps { children: React.ReactNode; label?: string; htmlFor?: string; error?: string; required?: boolean; className?: string; }
export function Field({ children, label, htmlFor, error, required, className }: FieldProps) {
  return (
    <div className={cn('flex flex-col', className)}>
      {label && <Label htmlFor={htmlFor} required={required}>{label}</Label>}
      {children}
      {error && <p className="text-caption text-[var(--danger)] mt-1">{error}</p>}
    </div>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, leftIcon, rightIcon, className, ...props }, ref) => (
    <div className="relative">
      {leftIcon && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none">
          {leftIcon}
        </span>
      )}
      <input
        ref={ref}
        className={cn(baseInput, error && errorInput, leftIcon && 'pl-9', rightIcon && 'pr-9', className)}
        {...props}
      />
      {rightIcon && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none">
          {rightIcon}
        </span>
      )}
    </div>
  )
);
Input.displayName = 'Input';

// ── Select ────────────────────────────────────────────────────────────────────
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: string;
  options: { value: string; label: string }[];
  placeholder?: string;
}
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ error, options, placeholder, className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        baseInput,
        'appearance-none cursor-pointer pr-8',
        'bg-[image:url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 16 16\'%3E%3Cpath fill=\'%2398A2B3\' d=\'M4 6l4 4 4-4\'/%3E%3C/svg%3E")] bg-no-repeat bg-[right_12px_center]',
        error && errorInput,
        className,
      )}
      {...props}
    >
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-[var(--bg-secondary)] text-[var(--text-primary)]">
          {o.label}
        </option>
      ))}
    </select>
  )
);
Select.displayName = 'Select';

// ── DateInput ─────────────────────────────────────────────────────────────────
interface DateInputProps extends React.InputHTMLAttributes<HTMLInputElement> { error?: string; }
export const DateInput = forwardRef<HTMLInputElement, DateInputProps>(
  ({ error, className, ...props }, ref) => (
    <input
      type="datetime-local"
      ref={ref}
      className={cn(
        baseInput,
        '[color-scheme:dark]',
        error && errorInput,
        className,
      )}
      {...props}
    />
  )
);
DateInput.displayName = 'DateInput';

// ── Checkbox ──────────────────────────────────────────────────────────────────
interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> { label?: string; }
export function Checkbox({ label, className, id, ...props }: CheckboxProps) {
  return (
    <label htmlFor={id} className="flex items-center gap-2 cursor-pointer group">
      <input
        type="checkbox"
        id={id}
        className={cn(
          'w-4 h-4 rounded-[4px] border border-[var(--card-border)]',
          'bg-[var(--bg-secondary)] appearance-none cursor-pointer',
          'checked:bg-[var(--info)] checked:border-[var(--info)]',
          'focus:ring-2 focus:ring-[var(--focus-ring)] outline-none',
          'transition-all duration-150',
          className,
        )}
        {...props}
      />
      {label && <span className="text-body text-[var(--text-primary)] group-hover:text-white transition-colors">{label}</span>}
    </label>
  );
}

// ── Toggle ────────────────────────────────────────────────────────────────────
interface ToggleProps { checked: boolean; onChange: (v: boolean) => void; label?: string; id?: string; }
export function Toggle({ checked, onChange, label, id }: ToggleProps) {
  return (
    <label htmlFor={id} className="flex items-center gap-3 cursor-pointer">
      <button
        id={id}
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative w-10 h-6 rounded-full transition-colors duration-200 outline-none',
          'focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]',
          checked ? 'bg-[var(--info)]' : 'bg-[var(--card-border)]',
        )}
      >
        <span className={cn(
          'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm',
          'transition-transform duration-200',
          checked ? 'translate-x-4' : 'translate-x-0',
        )} />
      </button>
      {label && <span className="text-body text-[var(--text-primary)]">{label}</span>}
    </label>
  );
}

// ── Textarea ──────────────────────────────────────────────────────────────────
interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> { error?: string; }
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ error, className, ...props }, ref) => (
    <textarea
      ref={ref}
      rows={3}
      className={cn(
        'w-full px-3 py-2.5 rounded-input resize-none',
        'bg-[var(--bg-secondary)] border border-[var(--card-border)]',
        'text-body text-[var(--text-primary)] placeholder:text-[var(--text-muted)]',
        'transition-all duration-150 outline-none',
        'focus:border-[var(--info)] focus:shadow-[0_0_0_3px_var(--focus-ring)]',
        'disabled:opacity-40',
        error && errorInput,
        className,
      )}
      {...props}
    />
  )
);
Textarea.displayName = 'Textarea';
