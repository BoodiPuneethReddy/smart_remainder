/**
 * lib/motion.ts — Shared Framer Motion animation variants.
 *
 * RULE: Every animated component imports from here.
 * No ad-hoc `transition={{...}}` or `animate={{...}}` duplicated per component.
 * Add new variants here first, then use them.
 */

import type { Variants } from 'framer-motion';

// ── Page transitions (200ms fade + 8px slide up) ───────────────────────────
export const fadeSlideIn: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: 0.15, ease: [0.4, 0, 1, 1] },
  },
};

// ── Staggered list children (50ms stagger between cards) ──────────────────
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: { staggerChildren: 0.05, delayChildren: 0.05 },
  },
};

export const staggerChild: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.22, ease: [0.4, 0, 0.2, 1] },
  },
};

// ── Toast / reminder spring entrance ──────────────────────────────────────
export const springIn: Variants = {
  initial: { opacity: 0, y: 20, scale: 0.95 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 380, damping: 26 },
  },
  exit: {
    opacity: 0,
    y: -12,
    scale: 0.96,
    transition: { duration: 0.18, ease: 'easeIn' },
  },
};

// ── Card hover lift (translateY -2px + shadow increase) ───────────────────
// Used as whileHover prop: <motion.div whileHover="hover" variants={liftOnHover}>
export const liftOnHover: Variants = {
  rest: { y: 0, transition: { duration: 0.15, ease: 'easeOut' } },
  hover: {
    y: -2,
    transition: { duration: 0.15, ease: 'easeOut' },
  },
};

// ── Task completion checkmark (scale 0 → 1.2 → 1 + fade in) ──────────────
export const checkComplete: Variants = {
  initial: { scale: 0, opacity: 0 },
  animate: {
    scale: [0, 1.2, 1],
    opacity: 1,
    transition: { duration: 0.35, ease: [0.34, 1.56, 0.64, 1] },
  },
};

// ── Skeleton pulse (for Skeleton components that use Framer Motion) ────────
export const skeletonPulse: Variants = {
  animate: {
    opacity: [0.5, 0.8, 0.5],
    transition: { duration: 1.8, repeat: Infinity, ease: 'linear' },
  },
};

// ── Modal / dropdown appear ────────────────────────────────────────────────
export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.96, y: 8 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.18, ease: [0.4, 0, 0.2, 1] },
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    y: 4,
    transition: { duration: 0.14, ease: 'easeIn' },
  },
};
