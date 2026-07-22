/**
 * components/ui/Button.tsx — Button variant system.
 *
 * Variants: primary | secondary | destructive | icon
 * Sizes: sm | md | lg
 * States: default, hover, active, disabled, loading
 *
 * Every state defined here — never override per page.
 */
import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export type ButtonVariant = 'primary' | 'secondary' | 'destructive' | 'icon';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  id?: string;
  'aria-label'?: string;
  form?: string;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: [
    'bg-[var(--info)] text-[var(--text-primary)]',
    'hover:bg-[#4a7de0] hover:brightness-110',
    'active:scale-[0.98] active:brightness-90',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'shadow-raised hover:shadow-raised-hover',
  ].join(' '),

  secondary: [
    'bg-transparent border border-[var(--card-border)] text-[var(--text-primary)]',
    'hover:bg-[var(--surface-hover)] hover:border-[var(--text-muted)]',
    'active:bg-[var(--surface-active)] active:scale-[0.98]',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),

  destructive: [
    'bg-[var(--danger)] text-white',
    'hover:brightness-110',
    'active:scale-[0.98] active:brightness-90',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),

  icon: [
    'bg-transparent text-[var(--text-secondary)]',
    'hover:bg-[var(--surface-hover)] hover:text-[var(--text-primary)]',
    'active:bg-[var(--surface-active)] active:scale-[0.95]',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'rounded-input',
  ].join(' '),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm:  'h-8 px-3 text-caption gap-1.5',
  md:  'h-10 px-4 text-body gap-2',
  lg:  'h-12 px-6 text-h3 gap-2',
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  className,
  disabled,
  type = 'button',
  onClick,
  id,
  'aria-label': ariaLabel,
}: ButtonProps) {
  const isIconOnly = variant === 'icon' && !children;

  return (
    <motion.button
      whileHover={!disabled && !loading ? { scale: 1.01 } : {}}
      whileTap={!disabled && !loading ? { scale: 0.98 } : {}}
      transition={{ duration: 0.15 }}
      id={id}
      type={type}
      onClick={onClick}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center justify-center font-medium select-none',
        'rounded-input transition-all duration-150 outline-none',
        'focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)]',
        variantStyles[variant],
        isIconOnly ? 'w-10 h-10 p-0' : sizeStyles[size],
        className,
      )}
      disabled={disabled || loading}
    >
      {loading ? (
        <Loader2
          size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16}
          className="animate-spin"
          aria-hidden
        />
      ) : (
        <>
          {icon && <span className="flex-shrink-0">{icon}</span>}
          {children && <span>{children}</span>}
        </>
      )}
    </motion.button>
  );
}
